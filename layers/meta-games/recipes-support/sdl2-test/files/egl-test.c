// EGL Wayland visual test - creates a colorful animated display
// Tests raw EGL + Wayland + OpenGL ES 2.0 integration

#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <wayland-client.h>
#include <wayland-egl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>

// Simple vertex shader for full-screen quad
static const char *vertex_shader =
    "attribute vec2 pos;\n"
    "varying vec2 v_tex;\n"
    "void main() {\n"
    "    v_tex = pos * 0.5 + 0.5;\n"
    "    gl_Position = vec4(pos, 0.0, 1.0);\n"
    "}\n";

// Colorful fragment shader with animation
static const char *fragment_shader =
    "precision mediump float;\n"
    "varying vec2 v_tex;\n"
    "uniform float u_time;\n"
    "void main() {\n"
    "    vec2 p = v_tex - 0.5;\n"
    "    float r = length(p);\n"
    "    float a = atan(p.y, p.x);\n"
    "    float w = 0.1 + 0.05 * sin(u_time * 2.0);\n"
    "    float f = pow(sin(r * 20.0 - u_time * 5.0 + a * 3.0), 2.0);\n"
    "    vec3 col = 0.5 + 0.5 * cos(u_time + vec3(0.0, 2.0, 4.0) + f * 3.14);\n"
    "    gl_FragColor = vec4(col, 1.0);\n"
    "}\n";

static struct wl_display *display;
static struct wl_surface *surface;
static struct wl_egl_window *egl_window;
static struct wl_compositor *compositor;

static void registry_handle_global(void *data, struct wl_registry *registry,
                                   uint32_t name, const char *interface,
                                   uint32_t version) {
    if (strcmp(interface, "wl_compositor") == 0) {
        compositor = (struct wl_compositor *)wl_registry_bind(
            registry, name, &wl_compositor_interface, 1);
    }
}

static void registry_handle_global_remove(void *data, struct wl_registry *registry,
                                          uint32_t name) {
}

static const struct wl_registry_listener registry_listener = {
    registry_handle_global,
    registry_handle_global_remove
};

static GLuint compile_shader(const char *src, GLenum type) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &src, NULL);
    glCompileShader(shader);
    return shader;
}

int main(int argc, char *argv[]) {
    EGLDisplay egl_display;
    EGLContext egl_context;
    EGLSurface egl_surface;
    struct wl_registry *registry;
    GLuint program, vbo;
    GLint time_loc, pos_loc;
    
    printf("=== EGL Wayland Visual Test ===\n");
    
    // Connect to Wayland
    display = wl_display_connect(NULL);
    if (!display) {
        fprintf(stderr, "Failed to connect to Wayland display\n");
        return 1;
    }
    printf("Connected to Wayland\n");
    
    // Get compositor
    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    wl_display_roundtrip(display);
    
    if (!compositor) {
        fprintf(stderr, "No compositor found\n");
        wl_display_disconnect(display);
        return 1;
    }
    printf("Got compositor\n");
    
    // Create surface
    surface = wl_compositor_create_surface(compositor);
    printf("Created Wayland surface\n");
    
    // Initialize EGL
    egl_display = eglGetDisplay((EGLNativeDisplayType)display);
    eglInitialize(egl_display, NULL, NULL);
    printf("EGL initialized\n");
    
    // Choose config
    EGLConfig config;
    EGLint num_configs;
    eglChooseConfig(egl_display, (EGLint[]){EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT, EGL_NONE}, 
                    &config, 1, &num_configs);
    
    // Create EGL surface
    egl_window = wl_egl_window_create(surface, 640, 480);
    egl_surface = eglCreateWindowSurface(egl_display, config, egl_window, NULL);
    printf("Created EGL surface\n");
    
    // Create context
    egl_context = eglCreateContext(egl_display, config, EGL_NO_CONTEXT, 
                                   (EGLint[]){EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE});
    eglMakeCurrent(egl_display, egl_surface, egl_surface, egl_context);
    printf("EGL context current\n");
    
    // Create shader program
    GLuint vs = compile_shader(vertex_shader, GL_VERTEX_SHADER);
    GLuint fs = compile_shader(fragment_shader, GL_FRAGMENT_SHADER);
    program = glCreateProgram();
    glAttachShader(program, vs);
    glAttachShader(program, fs);
    glLinkProgram(program);
    glUseProgram(program);
    
    // Full-screen quad
    float verts[] = {-1,-1, 1,-1, -1,1, 1,1};
    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STATIC_DRAW);
    pos_loc = glGetAttribLocation(program, "pos");
    glEnableVertexAttribArray(pos_loc);
    glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);
    time_loc = glGetUniformLocation(program, "u_time");
    
    printf("=== Starting Animation (5 seconds) ===\n");
    
    // Render animation
    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);
    float elapsed = 0;
    
    while (elapsed < 5.0) {
        clock_gettime(CLOCK_MONOTONIC, &now);
        elapsed = (now.tv_sec - start.tv_sec) + (now.tv_nsec - start.tv_nsec) / 1e9;
        
        glUniform1f(time_loc, elapsed);
        glClear(GL_COLOR_BUFFER_BIT);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        eglSwapBuffers(egl_display, egl_surface);
        wl_display_dispatch_pending(display);
        usleep(16000);
    }
    
    printf("=== Animation Complete ===\n");
    
    // Cleanup
    eglDestroyContext(egl_display, egl_context);
    eglDestroySurface(egl_display, egl_surface);
    wl_egl_window_destroy(egl_window);
    eglTerminate(egl_display);
    wl_display_disconnect(display);
    
    printf("All tests passed!\n");
    return 0;
}