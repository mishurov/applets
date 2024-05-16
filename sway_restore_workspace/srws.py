#! /usr/bin/env python3
from typing import Any, cast
import os
import re
import sys
import argparse
import json
import time
from socket import socket
from subprocess import Popen


from sway_ipc import (
    get_socket,
    get_tree,
    get_workspaces,
    command,
    find_con_parent_workspace,
)


class WorkspaceManager:
    LAUNCH_TIMOUT_SECONDS = 10
    EXECUTABLES = {
        'Alacritty': 'alacritty',
    }
    cwd: str | None = None
    layout_rect: dict[str, int] | None = None
    workspace_rect: dict[str, int] | None = None
    extracted_app_con_ids: list[int] = []

    def save_workspace(self, save_path: str, workspace_name: str) -> None:
        if os.path.exists(save_path) and not os.path.isfile(save_path):
            print(f'The specified path {save_path} is not a file')
            sys.exit(1)
        sock = get_socket()
        tree = get_tree(sock)
        search_name_fn = lambda n: n['name'] == workspace_name
        search_focused_fn = lambda n: n['focused']
        callback_fn = search_name_fn if workspace_name else search_focused_fn
        _, _, workspace_con = find_con_parent_workspace(tree, callback_fn)
        if workspace_con is None:
            print('No workspace found.')
            sys.exit(1)
        with open(save_path, 'w') as f:
            json.dump(workspace_con, f, indent=4)
        print(f'Saved JSON to {save_path}')

    def run_detached(self, cmd: str) -> None:
        Popen(
            cmd,
            shell=True,
            cwd=self.cwd,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
            start_new_session=True,
        )

    def get_scaled_size(
        self, node: dict[str, Any],
    ) -> tuple[int | None, int | None]:
        if self.workspace_rect is None or self.layout_rect is None:
            print('No workspace data to compute size!')
            return None, None
        l_rect = self.layout_rect
        w_rect = self.workspace_rect
        n_rect = node['rect']

        node_height = n_rect['height'] + node['deco_rect']['height']
        width_px = int(n_rect['width'] / l_rect['width'] * w_rect['width'])
        height_px = int(node_height / l_rect['height'] * w_rect['height'])
        return width_px, height_px

    def split(self, sock: socket, node: dict[str, Any]) -> None:
        layout = node['layout']
        orientation = node['orientation']
        if orientation == 'none':
            orientation = 'horizontal'
        res = command(sock, f'split {orientation}')
        print('Split result:', res)
        if layout != 'none':
            res = command(sock, f'layout {layout}')
            print('Layout result:', res)

    def find_apps(
        self,
        nodes: list[dict[str, Any]],
        apps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        for node in nodes:
            if 'app_id' in node:
                apps.append(node)
            self.find_apps(node['nodes'], apps)
        return apps

    def count_real_apps(self, sock: socket) -> int:
        tree = get_tree(sock)
        _, _, workspace = find_con_parent_workspace(
            tree, lambda n: n['focused'])
        apps = self.find_apps(workspace['nodes'], [])
        return len(apps)

    def launch(self, sock: socket, node: dict[str, Any]) -> None:
        cmd = node['app_id']
        if cmd in self.EXECUTABLES:
            cmd = self.EXECUTABLES[cmd]
        args = node.get('app_args', None)
        if args:
            cmd += ' ' + args
        print('Launching app:', cmd)
        apps_count = self.count_real_apps(sock)
        self.run_detached(cmd)
        new_apps_count = apps_count
        start_time = time.time()
        while new_apps_count <= apps_count:
            time.sleep(0.1)
            new_apps_count = self.count_real_apps(sock)
            end_time = time.time()
            if end_time - start_time > self.LAUNCH_TIMOUT_SECONDS:
                print('Launching app takes too long. Exiting.')
                sys.exit(1)
        tree = get_tree(sock)
        real_app_node, _, _ = find_con_parent_workspace(
            tree, lambda n: n['focused'])
        node['real_app_node'] = real_app_node

    def focus(self, sock: socket, node: dict[str, Any]) -> None:
        real_app_node = node.get('real_app_node', None)
        if real_app_node is None:
            print("Error: can't find real app node. Exiting.")
            sys.exit(1)
        con_id = real_app_node['id']
        res = command(sock, f'[con_id={con_id}] focus')
        print('Focus result:', res)

    def resize_real_app_nodes(
        self,
        sock: socket,
        subtree: dict[str, Any],
    ) -> None:
        for node in subtree['nodes']:
            app_node = node.get('app_node', None)
            if app_node and 'real_app_node' in app_node:
                real_app_node = app_node['real_app_node']
                con_id = real_app_node['id']
                width, height = self.get_scaled_size(app_node)
                res = command(
                    sock,
                    f'[con_id={con_id}] resize set {width} px {height} px',
                )
                print('Resize result:', res)
        for node in subtree['nodes']:
            self.resize_real_app_nodes(sock, node)

    def get_and_remember_app(
        self,
        node: dict[str, Any],
    ) -> dict[str, Any] | None:
        app_id = node.get('app_id', None)
        con_id = node.get('id', None)
        if app_id and con_id not in self.extracted_app_con_ids:
            self.extracted_app_con_ids.append(con_id)
            return node
        else:
            return None

    def find_first_deepest_app_node(
        self,
        subtree: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not len(subtree['nodes']):
            return self.get_and_remember_app(subtree)
        node = subtree['nodes'][0]
        if len(node['nodes']):
            deepest_app_node = self.find_first_deepest_app_node(node)
            if deepest_app_node:
                return deepest_app_node
        else:
            app_node = self.get_and_remember_app(node)
            if app_node is not None:
                return app_node
        return self.get_and_remember_app(subtree)

    def find_parent_app_node(
        self,
        node: dict[str, Any],
    ) -> dict[str, Any] | None:
        if 'app_node' in node:
            return cast(dict[str, Any], node['app_node'])
        elif 'parent' in node:
            return self.find_parent_app_node(node['parent'])
        else:
            return None

    def set_parents(self, subtree: dict[str, Any]) -> None:
        for node in subtree['nodes']:
            node['parent'] = subtree
            self.set_parents(node)

    def traverse(self, sock: socket, parent: dict[str, Any]) -> Any:
        nodes = parent['nodes']
        app_nodes = []
        for node in nodes:
            app_node = self.find_first_deepest_app_node(node)
            if app_node:
                node['app_node'] = app_node
                app_nodes.append(app_node)
        if len(app_nodes):
            focus_node = self.find_parent_app_node(parent)
            if focus_node:
                # print('focus', focus_node['app_id'])
                self.focus(sock, focus_node)

        if 'app_id' not in parent:
            # print('split', parent['orientation'])
            self.split(sock, parent)
        for app_node in app_nodes:
            # print('launch', app_node['app_id'])
            self.launch(sock, app_node)
        for node in nodes:
            self.traverse(sock, node)

    def load_workspace(self, load_path: str) -> None:
        if not os.path.isfile(load_path):
            print(f'The specified file {load_path} does not exist')
            sys.exit(1)
        workspace_con = None
        with open(load_path, 'r') as f:
            workspace_con = json.load(f)
        if workspace_con is None:
            print('Could not load JSON')
            sys.exit(1)
        if len(workspace_con['nodes']) == 0:
            print('The workspace has no nodes')
            sys.exit(1)

        workspace_name = workspace_con['name']
        new_name = re.sub('^[0-9]+', '', workspace_name)
        sock = get_socket()
        workspaces = get_workspaces(sock)
        num = 0
        current_workspace: dict[str, Any] | None = None
        for w in workspaces:
            num = w['num'] if num < w['num'] else num
            current_workspace = w
        if current_workspace is None:
            print('Could not find current workspace')
            sys.exit(1)

        res = command(sock, 'workspace {}'.format(str(num + 1) + new_name))
        print('Create workspace result:', res)

        self.cwd = os.path.dirname(os.path.realpath(load_path))

        self.layout_rect = workspace_con['rect']
        self.workspace_rect = cast(dict[str, int], current_workspace['rect'])
        self.set_parents(workspace_con)
        self.traverse(sock, workspace_con)
        self.resize_real_app_nodes(sock, workspace_con)

    def main(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument('--workspace')
        parser.add_argument('--save')
        parser.add_argument('--load')

        args = parser.parse_args()

        save_path = args.save
        load_path = args.load
        workspace_name = args.workspace

        if save_path:
            self.save_workspace(save_path, workspace_name)
            sys.exit(0)

        if load_path:
            self.load_workspace(load_path)
            sys.exit(0)

        print('Neither save or load files specified.')
        sys.exit(1)


if __name__ == '__main__':
    WorkspaceManager().main()
