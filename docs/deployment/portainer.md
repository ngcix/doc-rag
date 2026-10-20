# Deploying with Portainer

The stack is a single `compose.yaml` with prebuilt images. Each service mounts
one host folder at `/specrag`. In this repo that folder is `./data`; on the
node, point the `volumes` entries at the host folder you use. All settings are
fixed in `compose.yaml`; there is no `.env` file.

## Host layout

```text
<host folder>/
  config/setting.json            runtime settings
  models/embedding/              exported TEI model (+ rag.env, copied from export)
  documents/                     uploaded and indexed documents (written by rag)
  vectordb/, faiss_index/        index and metadata (written by rag)
  extracted_images/              images from PDFs (written by rag)
  process/                       sequence-chart and image outputs (written by rag)
```

Example for `/srv/specrag` on the node:

```bash
sudo mkdir -p /srv/specrag/{config,models/embedding,documents,vectordb,faiss_index,extracted_images,process}
sudo chown -R 1000:1000 /srv/specrag/{documents,vectordb,faiss_index,extracted_images,process}
```

## Images

Portainer does not build from local folders. Either:

- push the images to a registry the node can reach, and change the `image:`
  lines in `compose.yaml` to the registry names, or
- load them on the node: `gunzip -c specrag-images.tar.gz | docker load`.
  The names must be `specrag-rag:0.4.0` and `specrag-embedding:0.4.0`.

## Settings in compose.yaml

| Setting | Value | Change in |
|---------|-------|-----------|
| Host folder | `./data` here, `/srv/specrag` in the example | `volumes` of both services |
| API port (host) | `9999` → container 8080 | `rag.ports` |
| Embedding port (host) | `13333` → container 80 | `embedding.ports` |
| Images | `specrag-rag:0.4.0`, `specrag-embedding:0.4.0` | `image:` |
| Owner of data/process | `1000:1000` | `rag.user` |
| Model variant | `onnx-o3-fp32` | `rag.environment.EMBEDDING_MODEL_VARIANT` (must match `rag.env`) |
| Limits | embedding 4 CPU / 4g, rag 2 CPU / 10g | `cpus`, `mem_limit` |

## First start

1. Copy the model artifact into `models/embedding/` and `setting.json` into `config/`.
2. Deploy the stack. `embedding` must become healthy before `rag` starts.
3. Check `http://<node>:9999/api/v1/ready`.
4. Index documents with `specrag process -fp` (or the upload API). If the index
   was built with another model, rag refuses to use it. Run `specrag reindex -fp -y`.

## Notes

- The embedding port `13333` is published to all interfaces, so anyone who can
  reach the node can call the embedding API directly. Remove that `ports:` entry
  when testing is done.
- `rag` mounts the folder read-write because it writes the index, documents,
  images and `process/` there. The app does not write `config/` or `models/`,
  but the mount is read-write as a whole.
- `compose.dev.yaml` is for local development only and is not needed in Portainer.
