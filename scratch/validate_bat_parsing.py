import os
import sys

# Add parent directory to sys.path so we can import automate_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automate_pipeline import format_gemini_shots as run_format_loop

def test_validation():
    # 1. Mock shot events representing a session where:
    # - Shot 1: Facing up (no bat mentioned) -> should be None
    # - Shot 1: Cover Drive (no bat mentioned) -> should be None
    # - Shot 2: Admin / Stance mentioning "Gray Nicolls Giant" -> should set bat to "Gray Nicolls Giant"
    # - Shot 2: Straight Drive (no bat mentioned) -> should forward-fill "Gray Nicolls Giant"
    # - Shot 3: Cover Drive (no bat mentioned) -> should forward-fill "Gray Nicolls Giant"
    # - Shot 4: Facing up with text mentioning "changing to Eye In bat" -> should set bat to "Eye In"
    # - Shot 4: Flick Shot (no bat mentioned) -> should forward-fill "Eye In"
    # - Shot 5: Punch Shot with "game bat" mentioned in the text -> should set bat to "Game bat"
    # - Shot 6: Push Shot (no bat mentioned) -> should forward-fill "Game bat"
    
    mock_events = [
        {
            "shot_number": None,
            "timestamp_seconds": 10.0,
            "texts": ["facing up"],
            "bat": None
        },
        {
            "shot_number": 1,
            "timestamp_seconds": 15.0,
            "texts": ["cover drive good"],
            "bat": None
        },
        {
            "shot_number": None,
            "timestamp_seconds": 20.0,
            "texts": ["round 1 using Gray Nicolls Giant"],
            "bat": None
        },
        {
            "shot_number": 2,
            "timestamp_seconds": 25.0,
            "texts": ["straight drive excellent"],
            "bat": None
        },
        {
            "shot_number": 3,
            "timestamp_seconds": 30.0,
            "texts": ["cover drive okay"],
            "bat": None
        },
        {
            "shot_number": None,
            "timestamp_seconds": 35.0,
            "texts": ["facing up changing to Eye In bat"],
            "bat": None
        },
        {
            "shot_number": 4,
            "timestamp_seconds": 40.0,
            "texts": ["flick shot good"],
            "bat": None
        },
        {
            "shot_number": 5,
            "timestamp_seconds": 45.0,
            "texts": ["punch shot good game bat"],
            "bat": None
        },
        {
            "shot_number": 6,
            "timestamp_seconds": 50.0,
            "texts": ["push shot okay"],
            "bat": None
        }
    ]
    
    # We call the modified formatted_shots logic in automate_pipeline.py
    # Since formatted_shots in automate_pipeline expects event['texts'], we pass it.
    results = run_format_loop(mock_events)
    
    # Expected bat values for the output shots
    # Note: formatted_shots filters out events that do not resolve to a shot/facing-up,
    # but all our mock events should resolve. Let's inspect the outputs.
    
    print("\n--- Validation Results ---")
    for r in results:
        print(f"Time={r['timestamp_seconds']:.1f}s | Shot={r['shot_number']} | Type={r['shot_type']:<15} | Quality={r['quality']:<10} | Bat={str(r['bat']):<20} | Text='{r['narrated_text']}'")
        
    # Assertions
    # Shot 1 Cover Drive: bat should be None
    shot_1 = next(r for r in results if r["shot_number"] == 1 and r["shot_type"] == "Cover drive")
    assert shot_1["bat"] is None, "Expected Shot 1 to have no bat"
    
    # Shot 2: bat should be "Gray Nicolls Giant" (forward-filled from the round 1 announcement)
    shot_2 = next(r for r in results if r["shot_number"] == 2)
    assert shot_2["bat"] == "Gray Nicolls Giant", f"Expected Shot 2 to have 'Gray Nicolls Giant', got {shot_2['bat']}"
    
    # Shot 3: bat should be "Gray Nicolls Giant" (forward-filled)
    shot_3 = next(r for r in results if r["shot_number"] == 3)
    assert shot_3["bat"] == "Gray Nicolls Giant", f"Expected Shot 3 to have 'Gray Nicolls Giant', got {shot_3['bat']}"
    
    # Shot 4: bat should be "Eye In" (forward-filled from facing up announcement)
    shot_4 = next(r for r in results if r["shot_number"] == 4)
    assert shot_4["bat"] == "Eye In", f"Expected Shot 4 to have 'Eye In', got {shot_4['bat']}"
    
    # Shot 5: bat should be "Game bat" (explicitly matched from text)
    shot_5 = next(r for r in results if r["shot_number"] == 5)
    assert shot_5["bat"] == "Game bat", f"Expected Shot 5 to have 'Game bat', got {shot_5['bat']}"
    
    # Shot 6: bat should be "Game bat" (forward-filled)
    shot_6 = next(r for r in results if r["shot_number"] == 6)
    assert shot_6["bat"] == "Game bat", f"Expected Shot 6 to have 'Game bat', got {shot_6['bat']}"
    
    print("\n✅ All assertions passed! Validation of bat parsing and forward-filling is successful.")

if __name__ == "__main__":
    test_validation()
