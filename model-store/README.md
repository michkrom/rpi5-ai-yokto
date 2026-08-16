# model-store

Local cache of GGUF models for the yokto AI image.

Models here are pulled from the Pi (`/usr/share/models`) so that re-flashing
the SD card or setting up a new board does **not** require re-downloading from
HuggingFace.

```sh
tools/model-store.sh list              # what's on host vs device
tools/model-store.sh pull              # Pi -> ./model-store
tools/model-store.sh push              # ./model-store -> Pi /usr/share/models
tools/model-store.sh push root@<host>  # different target
```

The `.gguf` files themselves are gitignored (they live in `model-store/` on
disk only). After a `push`, run `ai-menu` on the device so it can point the
`llama-model.gguf` symlink at the preferred model, or just pick the model by
id in the menu.
