# yokto weston-init fixes for Raspberry Pi 5
# - Remove tty0 requirement (Pi5 may not have it)
# - Remove TTYPath requirement for headless operation
# - Add --continue-without-input for headless operation
# - Fix init.d script (meta-raspberrypi bbappend pattern doesn't match current init script)

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

do_install:append:rpi() {
    # Fix systemd service for headless operation
    if [ -e "${D}${systemd_system_unitdir}/weston.service" ]; then
        # Remove tty0 condition that can fail on Pi5
        sed -i '/ConditionPathExists=\/dev\/tty0/d' "${D}${systemd_system_unitdir}/weston.service"
        # Comment out TTY requirements for headless operation
        sed -i 's|^TTYPath=.*|#TTYPath=/dev/tty7|' "${D}${systemd_system_unitdir}/weston.service"
        sed -i 's|^TTYReset=yes|#TTYReset=yes|' "${D}${systemd_system_unitdir}/weston.service"
        sed -i 's|^TTYVHangup=yes|#TTYVHangup=yes|' "${D}${systemd_system_unitdir}/weston.service"
        sed -i 's|^TTYVTDisallocate=yes|#TTYVTDisallocate=yes|' "${D}${systemd_system_unitdir}/weston.service"
        sed -i 's|^StandardInput=tty-fail|#StandardInput=tty-fail|' "${D}${systemd_system_unitdir}/weston.service"
        # Ensure --continue-without-input is passed to weston (only if not already present)
        # The meta-raspberrypi bbappend already handles adding this flag, so we check first
        if ! grep -q '\-\-continue-without-input' "${D}${systemd_system_unitdir}/weston.service"; then
            sed -i 's|ExecStart=/usr/bin/weston |ExecStart=/usr/bin/weston --continue-without-input |' "${D}${systemd_system_unitdir}/weston.service"
            sed -i 's|ExecStart=/usr/bin/weston$|ExecStart=/usr/bin/weston --continue-without-input|' "${D}${systemd_system_unitdir}/weston.service"
        fi
    fi
    # Fix init.d script - the meta-raspberrypi bbappend pattern 'weston-start --' doesn't match
    # the actual script which has 'weston-start $OPTARGS'
    if [ -e "${D}/${sysconfdir}/init.d/weston" ]; then
        sed -i 's|weston-start \$OPTARGS|weston-start -- --continue-without-input \$OPTARGS|' "${D}/${sysconfdir}/init.d/weston"
    fi
}