#!/bin/sh

# set weston variables for use with global weston socket
global_socket="/run/wayland-0"
if [ -e "$global_socket" ]; then
	weston_group=$(stat -c "%G" "$global_socket")
	if [ "$(id -u)" = "0" ]; then
		export WAYLAND_DISPLAY="$global_socket"
	else
		case "$(groups "$USER")" in
			*"$weston_group"*)
				export WAYLAND_DISPLAY="$global_socket"
				;;
			*)
				;;
		esac
	fi
	unset weston_group
fi

# Also check for user-specific wayland socket (used when weston runs with user session)
if [ -z "$WAYLAND_DISPLAY" ]; then
	for sock in /run/user/*/wayland-1 /run/user/*/wayland-0; do
		if [ -e "$sock" ]; then
			export WAYLAND_DISPLAY="$sock"
			break
		fi
	done
fi

unset global_socket