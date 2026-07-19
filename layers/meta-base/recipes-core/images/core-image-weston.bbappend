ROOTFS_POSTPROCESS_COMMAND:append = " install_ssh_keys; "

install_ssh_keys() {
    install -d ${IMAGE_ROOTFS}/root/.ssh
    printf 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIESg0OSCNBfXLzGnKNifmJzPGn7Ji/XWFqJn7il+Vy33 m@norte\n' > ${IMAGE_ROOTFS}/root/.ssh/authorized_keys
    chmod 0600 ${IMAGE_ROOTFS}/root/.ssh/authorized_keys
}