"""Verify the scale-conditioned kernel-bandwidth MMD regression loss (module 3).

Checks the three theoretical properties claimed in 方法原理.md:
  1. Zero at coincidence: L(b, b) = 0.
  2. Scale invariance: L(k*b, k*b_gt) = L(b, b_gt) under joint scaling.
  3. Small-object sensitivity: fixed pixel offset -> smaller box gives larger loss.
Also checks that gradients flow through the loss.
"""
import torch
from ultralytics.utils.metrics import mmd_box_loss


def run():
    torch.manual_seed(0)

    # --- Property 1: zero at perfect match ---
    b = torch.tensor([[50.0, 50.0, 20.0, 20.0],   # 20x20 box at (50,50)
                      [100.0, 80.0, 5.0, 8.0]])   # 5x8 box at (100,80)
    l_same = mmd_box_loss(b, b)
    print("[P1] zero at coincidence:", l_same.tolist(), "-> max abs:", l_same.max().item())
    assert l_same.max().item() < 1e-6, "loss should be 0 when boxes coincide"

    # --- Property 2: scale invariance (joint scaling) ---
    gt = torch.tensor([[50.0, 50.0, 20.0, 20.0],
                       [100.0, 80.0, 5.0, 8.0]])
    pred = torch.tensor([[52.0, 48.0, 22.0, 18.0],
                         [101.0, 81.0, 6.0, 9.0]])
    l1 = mmd_box_loss(pred, gt)
    l2 = mmd_box_loss(2.0 * pred, 2.0 * gt)  # scale everything by k=2
    print("[P2] scale invariance: L:", l1.tolist(), " L(k*):", l2.tolist())
    assert torch.allclose(l1, l2, atol=1e-6), "loss must be invariant to joint scaling"

    # --- Property 3: small-object sensitivity (fixed offset) ---
    delta = 2.0
    gt_big = torch.tensor([[50.0, 50.0, 100.0, 100.0]])     # 100x100
    gt_small = torch.tensor([[50.0, 50.0, 10.0, 10.0]])     # 10x10
    pred_big = gt_big.clone(); pred_big[0, 0] += delta       # shift x by +2px
    pred_small = gt_small.clone(); pred_small[0, 0] += delta

    l_big = mmd_box_loss(pred_big, gt_big)
    l_small = mmd_box_loss(pred_small, gt_small)
    print("[P3] small-object sensitivity: big-box loss", l_big.item(),
          "| small-box loss", l_small.item())
    assert l_small.item() > l_big.item(), "smaller box must be penalized more for the same offset"

    # --- Gradients flow ---
    pred_g = pred_small.clone().requires_grad_(True)
    loss = mmd_box_loss(pred_g, gt_small).sum()
    loss.backward()
    print("[G] gradient norm:", pred_g.grad.norm().item())
    assert pred_g.grad is not None and pred_g.grad.abs().sum() > 0, "gradient must flow"

    print("\nAll checks passed.")


if __name__ == '__main__':
    run()
