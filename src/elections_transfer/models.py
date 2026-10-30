"""Estimators of per-cluster flow matrices J_k (2022 category × 2026 category).

Every estimator returns J with shape (K, C22, C26), raked so that each cluster's
row sums equal its observed 2022 counts and column sums its observed 2026 counts.

- cloud_vae: the main model. Each cluster is a Gaussian cloud of voters in a
  latent space, N(mu_k, sigma_k^2). The encoder sees only the cluster's 2022
  results (so 2026 is genuinely predicted, not memorised), and a KL term pulls
  each cloud toward N(0, I). A shared decoder maps each sampled voter z to:
    head="two":      a 2022 vote distribution and a 2026 vote distribution;
                     J_k = N_k E_z[p22(z) p26(z)^T]. With sharp > 0 each
                     sampled point pays for indecision (entropy), so it acts
                     like one voter who picks one list in each election.
    head="transfer": a 2022 vote distribution and a transfer matrix T(z), so the
                     2026 vote is conditioned on the 2022 vote;
                     J_k = N_k E_z[diag(p22(z)) T(z)]
    head="split":    z = (description, movement). The description code (latent
                     dims, KL weight beta) only reconstructs 2022. The small
                     movement code (t_latent dims, its own KL weight t_beta) is the
                     only thing that bends T away from the national matrix, and
                     2026 is predicted from the cluster's actual 2022 result:
                     p26 = s22 · E_z[T(z)], J_k = diag(x22_k) E_z[T(z)].
                     Otherwise whatever the code learns to describe a cluster
                     also lets T fit that cluster's noise.
  Averaged over sampled voters, the decoded votes must reproduce the cluster's
  2022 and 2026 vote shares. Every term (cross-entropy, KL, entropy) is in nats
  per voter and weighted by the cluster's number of voters, so each cluster makes
  the same fit-vs-information trade-off and the information its embedding carries
  is bounded by the objective itself, not by early stopping.
- constant: one transfer matrix T for the whole country, the same in every
  cluster (Goodman-style ecological regression): x26_k ≈ x22_k T.
- independent: no association within a cluster, J_k = x22_k x26_k^T / N_k. A
  lower bound on loyalty, useful as a reference.
"""

from dataclasses import asdict, dataclass, field

import numpy as np
import torch
from torch import nn

from .dataset import Dataset


def structural_mask(cats22: list[str], cats26: list[str]) -> np.ndarray:
    """1 where a flow is possible. Someone on neither the 2022 nor the 2026 roll
    isn't in the population, so NEW → LEFT is impossible."""
    mask = np.ones((len(cats22), len(cats26)))
    if "NEW" in cats22 and "LEFT" in cats26:
        mask[cats22.index("NEW"), cats26.index("LEFT")] = 0
    return mask


def rake(seed: np.ndarray, rows: np.ndarray, cols: np.ndarray, iters: int = 200, tol: float = 1e-6) -> np.ndarray:
    """Iterative proportional fitting of (K, I, J) seeds to row/column margins."""
    j = np.maximum(seed, 0).astype(float)
    for _ in range(iters):
        r = j.sum(2)
        j *= np.divide(rows, r, out=np.zeros_like(r), where=r > 0)[:, :, None]
        c = j.sum(1)
        j *= np.divide(cols, c, out=np.zeros_like(c), where=c > 0)[:, None, :]
        if np.abs(j.sum(2) - rows).max() < tol * max(1.0, rows.max()):
            break
    return j


@dataclass
class Result:
    name: str
    flows: np.ndarray  # (K, C22, C26), raked
    info: dict = field(default_factory=dict)

    @property
    def national(self) -> np.ndarray:
        return self.flows.sum(0)


def independent(ds: Dataset) -> Result:
    n = ds.n[:, None, None]
    seed = ds.x22[:, :, None] * ds.x26[:, None, :] / np.where(n > 0, n, 1)
    seed *= structural_mask(ds.cats22, ds.cats26)
    return Result("independent", rake(seed, ds.x22, ds.x26))


def constant(ds: Dataset, steps: int = 3000, lr: float = 0.05) -> Result:
    mask = torch.tensor(structural_mask(ds.cats22, ds.cats26), dtype=torch.float64)
    x22 = torch.tensor(ds.x22, dtype=torch.float64)
    x26 = torch.tensor(ds.x26, dtype=torch.float64)
    n = x22.sum(1, keepdim=True).clamp_min(1)
    logits = torch.zeros(mask.shape, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.Adam([logits], lr=lr)
    for _ in range(steps):
        t = torch.softmax(logits.masked_fill(mask == 0, -torch.inf), dim=1)
        loss = -(x26 * torch.log((x22 @ t) / n + 1e-12)).sum() / x26.sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    t = torch.softmax(logits.masked_fill(mask == 0, -torch.inf), dim=1).detach().numpy()
    seed = ds.x22[:, :, None] * t[None]
    return Result("constant", rake(seed, ds.x22, ds.x26), {"nll26": loss.item(), "T": t})


class CloudVAE(nn.Module):
    def __init__(self, c22: int, c26: int, latent: int, hidden: int, head: str, mask: torch.Tensor,
                 prior22: torch.Tensor, prior26: torch.Tensor, t_init: torch.Tensor | None = None,
                 t_latent: int = 0):
        super().__init__()
        self.c22, self.c26, self.latent, self.head = c22, c26, latent, head
        self.register_buffer("mask", mask)
        self.encoder = nn.Sequential(
            nn.Linear(c22 + 1, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(),
            nn.Linear(hidden, 2 * (latent + t_latent)),
        )
        if head == "split":
            self.decoder = nn.Sequential(
                nn.Linear(latent, hidden), nn.SiLU(),
                nn.Linear(hidden, hidden), nn.SiLU(),
                nn.Linear(hidden, c22),
            )
            self.t_decoder = nn.Sequential(
                nn.Linear(t_latent, hidden), nn.SiLU(),
                nn.Linear(hidden, hidden), nn.SiLU(),
                nn.Linear(hidden, c22 * c26),
            )
            with torch.no_grad():  # start exactly at the constant matrix
                self.decoder[-1].bias.copy_(torch.log(prior22 + 1e-6))
                self.t_decoder[-1].weight.zero_()
                self.t_decoder[-1].bias.copy_(torch.log(t_init + 1e-6).flatten())
            return
        out = c22 + (c26 if head == "two" else c22 * c26)
        self.decoder = nn.Sequential(
            nn.Linear(latent, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(),
            nn.Linear(hidden, out),
        )
        with torch.no_grad():
            # Start from national shares; the transfer head starts at the constant-matrix
            # fit with no dependence on z, so it departs from it only where the data pays.
            if head == "two":
                tail = torch.log(prior26 + 1e-6)
            else:
                tail = torch.log(t_init + 1e-6).flatten()
                self.decoder[-1].weight[c22:].zero_()
            self.decoder[-1].bias.copy_(torch.cat([torch.log(prior22 + 1e-6), tail]))

    def encode(self, s22, logn):
        mu, log_sigma = self.encoder(torch.cat([s22, logn[:, None]], 1)).chunk(2, dim=1)
        return mu, log_sigma.clamp(-6, 2)

    def decode(self, z, s22=None):
        """Per sampled voter: (p22, p26, joint-or-None). joint is (..., C22, C26).
        For the split head, s22 (the cluster's actual 2022 shares, (K, C22)) sets
        the 2022 composition that the transfer matrix acts on."""
        if self.head == "split":
            p22 = torch.softmax(self.decoder(z[..., : self.latent]), -1)
            t_logits = self.t_decoder(z[..., self.latent :]).unflatten(-1, (self.c22, self.c26))
            t = torch.softmax(t_logits.masked_fill(self.mask == 0, -torch.inf), -1)
            joint = s22[:, None, :, None] * t
            return p22, joint.sum(-2), joint
        else:
            logits = self.decoder(z)
            p22 = torch.softmax(logits[..., : self.c22], -1)
            if self.head == "two":
                return p22, torch.softmax(logits[..., self.c22 :], -1), None
            t_logits = logits[..., self.c22 :].unflatten(-1, (self.c22, self.c26))
        t = torch.softmax(t_logits.masked_fill(self.mask == 0, -torch.inf), -1)
        joint = p22[..., :, None] * t
        return p22, joint.sum(-2), joint


@dataclass
class VAEConfig:
    head: str = "transfer"  # "two" | "transfer" | "split"
    latent: int = 8
    beta: float = 1.0  # weight of the KL term vs. cross-entropy (both per voter)
    t_latent: int = 0  # split: movement-code dimensions
    t_beta: float = 0.0  # split: KL weight on the movement code
    sharp: float = 0.0  # entropy penalty on each sampled voter's vote distributions
    hidden: int = 128
    samples: int = 32  # voters sampled per cluster per step
    batch: int = 512  # clusters per step
    steps: int = 4000
    lr: float = 2e-3
    eval_samples: int = 1024
    seed: int = 0
    device: str = "cpu"

    @property
    def name(self) -> str:
        name = f"vae_{self.head}_d{self.latent}_b{self.beta:g}"
        if self.head == "split":
            name += f"_t{self.t_latent}_tb{self.t_beta:g}"
        name += f"_s{self.sharp:g}" if self.sharp else ""
        return name + (f"_n{self.steps}" if self.steps != VAEConfig.steps else "")

    @classmethod
    def from_name(cls, name: str, **kw) -> "VAEConfig":
        """Inverse of `name`, e.g. "vae_split_d20_b0.1_t4_tb3"."""
        head, *parts = name.removeprefix("vae_").split("_")
        fields = {"head": head}
        for part in parts:
            for prefix, key, cast in (("tb", "t_beta", float), ("t", "t_latent", int), ("d", "latent", int),
                                      ("b", "beta", float), ("s", "sharp", float), ("n", "steps", int)):
                if part.startswith(prefix):
                    fields[key] = cast(part[len(prefix):])
                    break
        return cls(**{**fields, **kw})


def _tensors(ds: Dataset, device: str):
    x22 = torch.tensor(ds.x22, dtype=torch.float32, device=device)
    x26 = torch.tensor(ds.x26, dtype=torch.float32, device=device)
    n = x22.sum(1).clamp_min(1)
    logn = torch.log(n)
    logn = (logn - logn.mean()) / logn.std()
    return x22, x26, n, logn


def _kl(mu, log_sigma):
    return 0.5 * (mu.pow(2) + (2 * log_sigma).exp() - 1 - 2 * log_sigma).sum(-1)


def cloud_vae(ds: Dataset, cfg: VAEConfig = VAEConfig(), log_every: int = 0, t_init: np.ndarray | None = None) -> Result:
    torch.manual_seed(cfg.seed)
    dev = cfg.device
    x22, x26, n, logn = _tensors(ds, dev)
    s22 = x22 / n[:, None]
    mask = torch.tensor(structural_mask(ds.cats22, ds.cats26), dtype=torch.float32)
    if cfg.head in ("transfer", "split"):
        t_init = torch.tensor(constant(ds).info["T"] if t_init is None else t_init, dtype=torch.float32)
    t_latent = cfg.t_latent if cfg.head == "split" else 0
    dims = cfg.latent + t_latent
    model = CloudVAE(
        ds.x22.shape[1], ds.x26.shape[1], cfg.latent, cfg.hidden, cfg.head, mask,
        prior22=(x22.sum(0) / x22.sum()).cpu(), prior26=(x26.sum(0) / x26.sum()).cpu(), t_init=t_init,
        t_latent=t_latent,
    ).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, cfg.steps, eta_min=cfg.lr / 20)
    k = len(n)
    history = []
    for step in range(cfg.steps):
        idx = torch.randint(0, k, (min(cfg.batch, k),), device=dev)
        mu, log_sigma = model.encode(s22[idx], logn[idx])
        eps = torch.randn(len(idx), cfg.samples, dims, device=dev)
        p22, p26, _ = model.decode(mu[:, None, :] + log_sigma.exp()[:, None, :] * eps, s22[idx])
        q22, q26 = p22.mean(1), p26.mean(1)
        nll = -(x22[idx] * torch.log(q22 + 1e-9)).sum() - (x26[idx] * torch.log(q26 + 1e-9)).sum()
        # Everything weighted by voters: w_k = N_k / sum N over the batch.
        w = n[idx] / n[idx].sum()
        nll_per_voter = nll / n[idx].sum()
        d = cfg.latent
        kl_per_voter = (w * _kl(mu[:, :d], log_sigma[:, :d])).sum()
        kl_move = (w * _kl(mu[:, d:], log_sigma[:, d:])).sum()
        loss = nll_per_voter + cfg.beta * kl_per_voter + cfg.t_beta * kl_move
        if cfg.sharp:
            entropy = -(p22 * torch.log(p22 + 1e-9)).sum(-1).mean(1) - (p26 * torch.log(p26 + 1e-9)).sum(-1).mean(1)
            loss = loss + cfg.sharp * (w * entropy).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        if log_every and (step % log_every == 0 or step == cfg.steps - 1):
            rec = {"step": step, "nll": nll_per_voter.item(), "kl": kl_per_voter.item(), "kl_move": kl_move.item()}
            history.append(rec)
            print(f"  step {step:5d}  cross-entropy {rec['nll']:.4f}  kl {rec['kl']:.2f}  kl_move {rec['kl_move']:.3f}")

    flows, fit = _vae_flows(model, ds, cfg)
    return Result(cfg.name, flows, {"config": asdict(cfg), "fit": fit, "history": history})


@torch.no_grad()
def _vae_flows(model: CloudVAE, ds: Dataset, cfg: VAEConfig, chunk: int = 64):
    dev = cfg.device
    x22, x26, n, logn = _tensors(ds, dev)
    s22 = x22 / n[:, None]
    g = torch.Generator(device=dev).manual_seed(cfg.seed + 1)
    seeds, pred22, pred26, kls = [], [], [], []
    for a in range(0, len(n), chunk):
        sl = slice(a, a + chunk)
        mu, log_sigma = model.encode(s22[sl], logn[sl])
        eps = torch.randn(mu.shape[0], cfg.eval_samples, mu.shape[1], generator=g, device=dev)
        p22, p26, joint = model.decode(mu[:, None, :] + log_sigma.exp()[:, None, :] * eps, s22[sl])
        if joint is None:
            seeds.append((torch.einsum("ksi,ksj->kij", p22, p26) / cfg.eval_samples).cpu())
        else:
            seeds.append(joint.mean(1).cpu())
        pred22.append(p22.mean(1).cpu())
        pred26.append(p26.mean(1).cpu())
        kls.append(torch.stack([_kl(mu[:, : cfg.latent], log_sigma[:, : cfg.latent]),
                                _kl(mu[:, cfg.latent :], log_sigma[:, cfg.latent :])], 1).cpu())
    seed = torch.cat(seeds).double().numpy() * ds.n[:, None, None]
    seed *= structural_mask(ds.cats22, ds.cats26)
    q22, q26 = torch.cat(pred22).double().numpy(), torch.cat(pred26).double().numpy()

    def gap(x, q):  # KL(observed shares || predicted shares), nats per voter
        p = x / np.maximum(x.sum(1, keepdims=True), 1)
        return float((x * (np.log(np.maximum(p, 1e-12)) - np.log(np.maximum(q, 1e-12)))).sum() / x.sum())

    kls = torch.cat(kls)
    fit = {"gap22": gap(ds.x22, q22), "gap26": gap(ds.x26, q26),
           "kl_per_cluster": float(kls[:, 0].mean()), "kl_move_per_cluster": float(kls[:, 1].mean())}
    return rake(seed, ds.x22, ds.x26), fit
