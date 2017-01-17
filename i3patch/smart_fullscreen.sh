#!/bin/sh

if ( i3-msg zoom 3>&1 1>&2- 2>&3- ) | grep -q "\^\^"
then
    maximize_action=fullscreen
    maximize_var=fullscreen_mode
else
    maximize_action=zoom
    maximize_var=zoomed
fi

get_workspace_name () {
    echo $(i3-msg -t get_workspaces | jq \
    ".[] | select(.focused == true) | .name" \
    | tr -d '"')
}

fullscreen_enable () {
    # i3-msg bar hidden_state hide
    # i3-msg bar mode hide
    i3-msg $1 $maximize_action enable
    #if [ $maximize_action = "zoom" ] ; then
    #    i3-msg $1 rename workspace to "$(get_workspace_name)*Z"
    #fi
}

fullscreen_disable () {
    # i3-msg bar mode dock
    i3-msg $1 $maximize_action disable
    #if [ $maximize_action = "zoom" ] && \
    #get_workspace_name | grep -q "\*Z"
    #then
    #    i3-msg $1 rename workspace to \
    #    "$(get_workspace_name | head -c -3)"
    #fi
}

is_fullscreen() {
    con_type=$(echo "$1" | awk '{print $1}')
    is_fullscreen=$(echo "$1" | awk '{print $2}')
    if [ "$con_type" != "workspace" -a "$is_fullscreen" = "true" ] ; then
        return 0
    fi
    return 1
}

focused_data=$(i3-msg -t get_tree | jq "recurse(.nodes[]) \
    | select(.focused == true) 
    | \"\(.type) \(.${maximize_var}) \(.layout) \(.id)\" " | tr -d '"')

echo "FOCUS POCUS" $focused_data

if is_fullscreen "$focused_data" ; then
    fullscreen_disable
    exit 0
fi

child_id=$(echo "$focused_data" | awk '{print $4}')

parent_data=$(i3-msg -t get_tree | jq "recurse(.nodes[]) \
    | select(contains({ nodes: [{id: $child_id}] })) \
    | \"\(.type) \(.${maximize_var}) \(.layout) \(.id) \(.nodes | length)\" " | tr -d '"')
parent_id=$(echo "$parent_data" | awk '{print $4}')

if is_fullscreen "$parent_data" ; then
    i3-msg "[con_id=\"$parent_id\"] focus"
    fullscreen_disable
    i3-msg "[con_id=\"$child_id\"] focus"
    exit 0
fi

con_type=$(echo "$parent_data" | awk '{print $1}')
parent_layout=$(echo "$parent_data" | awk '{print $3}')
children=$(echo "$parent_data" | awk '{print $5}')

if [ "$con_type" != "workspace" \
   -a "$parent_layout" = "tabbed" \
   -o "$parent_layout" = "stacked" ]
then
    i3-msg "[con_id=\"$parent_id\"] focus"
    fullscreen_enable
    i3-msg "[con_id=\"$child_id\"] focus"
    exit 0
fi

if ! [ "$maximize_action" = "zoom" \
       -a "$con_type" = "workspace" \
       -a "$children" -le 1 ]
then
  fullscreen_enable
fi
