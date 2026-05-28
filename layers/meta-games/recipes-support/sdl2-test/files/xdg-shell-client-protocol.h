// Pre-generated xdg-shell client protocol header
// This is a minimal stub for the egl-test

#ifndef XDG_SHELL_CLIENT_PROTOCOL_H
#define XDG_SHELL_CLIENT_PROTOCOL_H

#include <stdint.h>
#include <stddef.h>

struct wl_surface;
struct wl_output;

struct xdg_surface;
struct xdg_toplevel;
struct xdg_wm_base;

static inline void xdg_wm_base_pong(struct xdg_wm_base *xdg_wm_base, uint32_t serial) {}

static inline struct xdg_surface* xdg_wm_base_get_xdg_surface(struct xdg_wm_base *xdg_wm_base, struct wl_surface *surface) {
    return (struct xdg_surface*)surface;
}

static inline struct xdg_toplevel* xdg_surface_get_toplevel(struct xdg_surface *xdg_surface) {
    return (struct xdg_toplevel*)xdg_surface;
}

static inline void xdg_toplevel_add_listener(struct xdg_toplevel *xdg_toplevel, const void *listener, void *data) {}

static inline void xdg_surface_commit(struct xdg_surface *xdg_surface) {}

#endif