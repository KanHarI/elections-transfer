"""Command-line entry point: elections-transfer {download,synth,fit,export,all,serve}."""

import argparse
import functools
import http.server
import json
import pickle
from pathlib import Path

import torch

from . import data, dataset, models, synthetic
from .data import ROOT

RESULTS = ROOT / "results"


def _device(arg: str) -> str:
    if arg != "auto":
        return arg
    return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


def grid(device: str) -> list[models.VAEConfig]:
    two = [(1, 0), (1, 0.3), (3, 0.3)]
    cfgs = [models.VAEConfig(head="two", latent=8, beta=b, sharp=s, device=device) for b, s in two]
    transfer = [(4, 0.3), (4, 1), (4, 3), (4, 10), (8, 1), (8, 3)]
    cfgs += [models.VAEConfig(head="transfer", latent=d, beta=b, device=device) for d, b in transfer]
    return cfgs


def serve(port: int):
    """Serve web/ locally, telling the browser to revalidate every file so edits show up."""

    class NoCache(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

    handler = functools.partial(NoCache, directory=str(ROOT / "web"))
    print(f"Serving web/ at http://127.0.0.1:{port}")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="elections-transfer")
    ap.add_argument("command", choices=["download", "synth", "fit", "export", "all", "serve"])
    ap.add_argument("--port", type=int, default=8765, help="serve: port on 127.0.0.1")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--heads", help="synth: comma-separated decoder heads (default: built-in grid)")
    ap.add_argument("--latent", type=int, help="synth: latent dimensions")
    ap.add_argument("--betas", help="synth: comma-separated KL weights")
    ap.add_argument("--t-latent", type=int, default=4, help="synth, split head: movement-code dimensions")
    ap.add_argument("--t-betas", default="3", help="synth, split head: comma-separated movement KL weights")
    ap.add_argument("--steps", type=int, help=f"VAE training steps (default {models.VAEConfig.steps}; --vae names may set it)")
    ap.add_argument("--tag", default="", help="synth: results go to results/synthetic[_tag].csv")
    ap.add_argument("--vae", help="fit: config name to fit instead of the best synthetic one, e.g. vae_split_d20_b0.1_t4_tb3")
    args = ap.parse_args(argv)
    if args.command == "serve":
        return serve(args.port)
    device = _device(args.device)
    RESULTS.mkdir(exist_ok=True)

    if args.command in ("download", "all"):
        for k in (25, 26):
            print(f"K{k}:", json.dumps(data.download(k), ensure_ascii=False))

    ds = dataset.build()
    print(json.dumps(ds.summary, ensure_ascii=False, default=float))

    if args.command in ("synth", "all"):
        if args.heads:
            cfgs = [
                models.VAEConfig(head=h, latent=args.latent, beta=float(b), steps=args.steps or models.VAEConfig.steps, device=device,
                                 t_latent=args.t_latent if h == "split" else 0,
                                 t_beta=float(tb) if h == "split" else 0.0)
                for h in args.heads.split(",") for b in args.betas.split(",")
                for tb in (args.t_betas.split(",") if h == "split" else ["0"])
            ]
        else:
            cfgs = grid(device)
        df = synthetic.run(ds, cfgs, out=RESULTS / f"synthetic{'_' + args.tag if args.tag else ''}.csv")
        print(df.groupby("model")[["party_row_tv", "cluster_tv"]].mean().sort_values("party_row_tv"))
        print("SYNTH DONE")

    if args.command in ("fit", "all"):
        from .export import chosen_config

        if args.vae:
            cfg = models.VAEConfig.from_name(args.vae, device=device, **({"steps": args.steps} if args.steps else {}))
        else:
            cfg = chosen_config(device)
        fits = [models.constant(ds), models.cloud_vae(ds, cfg, log_every=1000)]
        with open(RESULTS / "fits.pkl", "wb") as f:
            pickle.dump({"dataset": ds, "fits": fits}, f)

    if args.command in ("export", "all"):
        from . import export

        export.write()


if __name__ == "__main__":
    main()
