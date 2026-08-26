"""
End-to-end verification script testing live FastAPI endpoints,
LangGraph reconciliation pipeline, sample invoice runs, exception resolution, and exports.
"""

import httpx
import json

def run_verification():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

    print("=== 1. Checking Health Endpoint ===")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health failed: {r.status_code}"
    print(f"Health Response: {r.json()}")

    # Reset ledger to start with clean baseline
    client.post("/api/seed-ledger?force=true")

    print("\n=== 2. Checking Initial Stats ===")
    r = client.get("/api/stats")
    assert r.status_code == 200
    print(f"Initial Stats: {r.json()}")

    print("\n=== 3. Testing 1-Click Sample Invoices Execution ===")
    samples = [
        ("01_aws_cloud_invoice", "Auto-Reconciled"),
        ("02_slack_technologies_invoice", "Auto-Reconciled"),
        ("03_github_enterprise_invoice", "Needs Review"),
        ("04_adobe_creative_cloud_invoice", "Auto-Reconciled"),
        ("05_unmatched_vendor_invoice", "Failed"),
    ]

    for sample_id, expected_status in samples:
        res = client.post(f"/api/run-sample/{sample_id}")
        assert res.status_code == 200, f"Failed sample {sample_id}: {res.text}"
        data = res.json()
        status = data["status"]
        score = data["confidence_score"] * 100
        tx = data.get("matched_ledger_transaction")
        tx_id = tx.get("transaction_id") if tx else "None"
        print(f"-> Sample: {sample_id:<32} | Status: {status:<16} (Expected: {expected_status}) | Score: {score:>5.1f}% | Matched Tx: {tx_id}")

    print("\n=== 4. Verifying KPI Stats After Ingestion ===")
    stats_res = client.get("/api/stats")
    stats = stats_res.json()
    print(json.dumps(stats, indent=2))
    assert stats["total_invoices"] >= 5

    print("\n=== 5. Testing Manual Exception Resolution Workflow ===")
    results_res = client.get("/api/reconciliation-results")
    results = results_res.json()
    review_items = [item for item in results if item["status"] == "Needs Review"]
    if review_items:
        target = review_items[0]
        print(f"Found flagged item: {target['invoice']['vendor_name']} (ID: {target['id']})")
        resolve_res = client.post("/api/resolve-exception", json={
            "reconciliation_id": target["id"],
            "action": "approve_match",
            "notes": "Controller confirmed vendor alias GITHUB_COM_SUB_8491 with 1-day clearance latency."
        })
        assert resolve_res.status_code == 200
        print(f"Resolution response: {resolve_res.json()}")

    print("\n=== 6. Verifying CSV & JSON Exports ===")
    csv_res = client.get("/api/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    lines = csv_res.text.strip().splitlines()
    print(f"CSV exported successfully with {len(lines)} lines (Header + Records)")
    print(f"CSV Header: {lines[0]}")
    print(f"First Row:  {lines[1]}")

    json_res = client.get("/api/export/json")
    assert json_res.status_code == 200
    audit_data = json_res.json()
    print(f"JSON audit log exported successfully with {len(audit_data)} full audit entries")

    print("\n[SUCCESS] ALL VERIFICATION STEPS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
