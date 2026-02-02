import sys
import os

# Mocking the classify logic to test it in isolation
def classify_category(title, summary, current_cat):
    if current_cat == 'hand': return 'hand'
    
    keywords_hand = ["hand", "gripper", "finger", "manipulation", "dexterous", "tactile", "grasping", "핸드", "그리퍼", "손", "매니퓰", "촉각", "파지"]
    keywords_humanoid = ["humanoid", "bipedal", "walking", "locomotion", "torso", "human-centered", "휴머노이드", "이족보행", "보행", "로코모션"]
    
    text = (title + " " + (summary or "")).lower()
    
    for kw in keywords_hand:
        if kw in text:
            return "hand"
            
    for kw in keywords_humanoid:
        if kw in text:
            return "humanoid"
            
    return current_cat

# Test cases
test_cases = [
    # (Title, Summary, SourceCat, ExpectedFinalCat, ShouldKeep)
    ("New Humanoid Robot Unveiled", "It can walk efficiently.", "paper", "humanoid", True),
    ("Dexterous Manipulation with Soft Hands", "Grasping novel objects.", "paper", "hand", True),
    ("Optimizing Drone Flight Paths", "Algorithm for quadcopters.", "paper", "paper", False),
    ("Reinforcement Learning for Locomotion", "Bipedal robots learning to walk.", "paper", "humanoid", True),
    ("Computer Vision for Traffic Analysis", "Detecting cars in video.", "paper", "paper", False),
    ("General Robotics News", "Some robot news.", "humanoid", "humanoid", True), # Should keep source cat if not paper or if match
]

print("🧪 Testing Filtering Logic...")
failed = False
for title, summary, src_cat, expected_cat, should_keep in test_cases:
    final_cat = classify_category(title, summary, src_cat)
    kept = not (src_cat == 'paper' and final_cat == 'paper')
    
    if final_cat != expected_cat:
        print(f"❌ Classification Match Failed: '{title}' -> Expected {expected_cat}, Got {final_cat}")
        failed = True
    elif kept != should_keep:
        print(f"❌ Filtering Action Failed: '{title}' -> Expected Keep={should_keep}, Got Keep={kept}")
        failed = True
    else:
        status = "✅ Kept" if kept else "🚫 Filtered"
        print(f"{status}: '{title}' -> {final_cat}")

if failed:
    sys.exit(1)
else:
    print("\nAll tests passed successfully!")
