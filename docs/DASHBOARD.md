# Visual Operations Dashboard

The dashboard is a credential-free, read-only view over four bundled synthetic
operations snapshots. It makes the platform's trust controls visible without
connecting to a live asset, market, meter, dispatch adapter, or settlement system.

## Run locally

```bash
python -m pip install -e ".[dashboard]"
python app.py
```

Open `http://127.0.0.1:7860`.

## Views

| Scenario | Purpose | Expected disposition |
|---|---|---|
| Healthy coordination | Complete evidence and valid audit chain | Normal |
| Capacity stress | Low headroom and delivery variance | Review |
| Meter evidence gap | Missing in-window evidence | Block |
| Audit tampering detected | Hash-chain verification failure | Block |

Each view presents fleet capacity, reservations, dispatch, delivered energy,
evidence coverage, settlement readiness, trust controls, asset-level state, and a
synthetic event timeline.

## Safety boundary

- Data is loaded from a versioned JSON package fixture marked as synthetic.
- The dashboard does not read the platform database.
- It does not send API requests or invoke a dispatch publisher.
- It has no authentication or authorization claim.
- A status is a demonstration signal, not permission to dispatch or settle.

The transactional API remains the executable reference workflow. The dashboard
is an explanatory operations surface for reviewers and portfolio demonstrations.
