def test_saved_items_api(client, auth_headers):
    # 1. Get initial saved items
    get_res = client.get("/api/v1/saved", headers=auth_headers)
    assert get_res.status_code == 200
    assert isinstance(get_res.json(), list)

    # 2. Save an item
    save_res = client.post(
        "/api/v1/saved",
        json={"item_type": "community", "item_id": 1},
        headers=auth_headers
    )
    assert save_res.status_code == 201
    assert save_res.json()["item_id"] == 1

    # 3. Verify in saved list
    saved_list = client.get("/api/v1/saved", headers=auth_headers).json()
    assert any(item["item_id"] == 1 and item["item_type"] == "community" for item in saved_list)

    # 4. Unsave item
    del_res = client.delete("/api/v1/saved/community/1", headers=auth_headers)
    assert del_res.status_code == 200

def test_discovery_search_api(client):
    res = client.post(
        "/api/v1/discovery/search",
        json={"query": "AI machine learning python", "limit": 6}
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "score" in first
    assert "reason" in first
    assert "title" in first
