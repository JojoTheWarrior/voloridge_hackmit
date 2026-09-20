from warsignal.ai import jev_client


def test_heuristic_scores_are_0_to_10_and_cross_domain_is_more_interesting(monkeypatch):
    monkeypatch.setattr(jev_client, "_openai_fallback", lambda state: (_ for _ in ()).throw(RuntimeError("offline")))
    base = {
        "n_obs": 100,
        "perm_p": 0.04,
        "correlation": {"pearson_r": 0.5},
    }
    same = jev_client._fallback({**base, "plan": {"indicator_a": "finance.BZ=F.close", "indicator_b": "finance.CL=F.close"}}, {})
    cross = jev_client._fallback({**base, "plan": {"indicator_a": "gdelt.irn.events", "indicator_b": "finance.BZ=F.close"}}, {})
    for result in (same, cross):
        assert all(0 <= value <= 10 for value in result["scores"].values())
    assert cross["scores"]["interestingness"] > same["scores"]["interestingness"]
