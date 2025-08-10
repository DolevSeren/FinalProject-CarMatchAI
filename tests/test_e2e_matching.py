from services.matching.matcher import UserProfile, CarItem, match

# נריץ התאמה על דאטה סינתטי קטן כדי לוודא שהציון והסינון עובדים ולא קורסים על import

def test_e2e_matching_basic_any():
    p = UserProfile(
        condition="any",
        budget=30000,
        passengers=4,
        terrain="flat",
        likes=["hybrid"],
        dislikes=["diesel"],
    )

    new_inv = [
        CarItem(make="Toyota", model="Camry", price=29000, segment="midsize", seats=5, fuel="hybrid", is_new=True, meta={"OverallRating": 5}),
        CarItem(make="Honda", model="Civic", price=26000, segment="compact", seats=5, fuel="petrol", is_new=True, meta={}),
    ]

    used_inv = [
        CarItem(make="BMW", model="3 Series", price=28000, segment="premium-compact", seats=5, fuel="petrol", is_new=False, meta={"reliability_score": 3}),
        CarItem(make="Volkswagen", model="Passat", price=18000, segment="midsize", seats=5, fuel="diesel", is_new=False, meta={}),
    ]

    res = match(p, new_inv, used_inv, top_n=3)
    assert len(res) >= 1
    # Toyota Camry Hybrid אמור להופיע גבוה ברשימה בזכות התאמה ל-likes + בטיחות
    assert any(r.make == "Toyota" and r.model == "Camry" for r in res)


def test_e2e_matching_new_only():
    p = UserProfile(condition="new", budget=27000, passengers=4)
    new_inv = [
        CarItem(make="Toyota", model="Corolla", price=25000, segment="compact", seats=5, fuel="hybrid", is_new=True, meta={}),
        CarItem(make="Hyundai", model="Elantra", price=23000, segment="compact", seats=5, fuel="petrol", is_new=True, meta={}),
    ]
    used_inv = []
    res = match(p, new_inv, used_inv, top_n=2)
    assert len(res) == 2
    assert all(r.is_new for r in res)