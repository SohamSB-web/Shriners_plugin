import ezc3d

c = ezc3d.c3d(r"C:\Users\ADMIN\Music\Shriners_plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-18_2\Static 3.c3d")




print("All C3D parameter groups:")
print(list(c["parameters"].keys()))

print("\nAll PROCESSING parameters:")
processing = c["parameters"].get("PROCESSING", {})

if not processing:
    print("PROCESSING group is missing or empty.")
else:
    for key, item in processing.items():
        print(f"{key}: {item.get('value')}")
