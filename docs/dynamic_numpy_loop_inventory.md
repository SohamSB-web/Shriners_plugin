# Dynamic processing loop inventory (original source)

Includes every for/while and comprehension in the eight requested files. Calls include nested branches; a listed call is not necessarily executed in every configuration.

## Py3_DynamicMain.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 136–136 | MarkerArrayCheck | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 137–137 | MarkerArrayCheck | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 138–138 | MarkerArrayCheck | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 151–153 | __init__ | `for measurement_name in measurement_names:` | Partially vectorizable | float, setattr, getattr, abs |
| 156–165 | __init__ | `for (opt, default_val) in [('valuePelvicFixCheck', '0'), ('valueKneeAlignmentCheck', '0'), ('valueLeftFootModelCheck', '0'), ('valueRightFootModelCheck', '0'), ('valueLeftSoleThickness', '0'), ('valueRightSoleThickness', '0')]:` | Partially vectorizable | hasattr, setattr |
| 233–233 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 234–234 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 235–235 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 236–236 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 237–237 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 238–238 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 241–309 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range, math.TransformPointIntoLabCoors, np.array, gait.TechCS_Pelvis_Newington |
| 378–378 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 379–379 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 380–380 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 382–382 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 383–383 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 384–384 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 388–388 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 389–389 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 390–390 | __init__ | `[30 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 393–393 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 394–394 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 395–395 | __init__ | `[30 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 399–476 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range, np.array, gait.TechCS_Forefoot_mSHCG, math.TransformPointIntoLabCoors |
| 576–576 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 577–577 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 578–578 | __init__ | `[0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 579–588 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range |
| 815–819 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range |
| 890–890 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 890–890 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 891–891 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 891–891 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 892–892 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 892–892 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 893–893 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 893–893 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 894–894 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 894–894 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 895–895 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 895–895 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 898–898 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 898–898 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 899–899 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 899–899 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 900–900 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 900–900 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 901–901 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 901–901 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 902–902 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 902–902 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 903–903 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 903–903 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 906–906 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 906–906 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 908–908 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 908–908 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 910–910 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 910–910 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 912–912 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 912–912 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 913–913 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 913–913 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 914–914 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 914–914 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 915–915 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 915–915 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 916–916 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 916–916 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 917–917 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 917–917 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 918–918 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 918–918 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 919–919 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 919–919 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 920–920 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 920–920 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 922–924 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 923–923 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 925–927 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 926–926 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 928–928 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 928–928 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 930–930 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 930–930 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 931–931 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 931–931 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 932–932 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 932–932 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 933–933 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 933–933 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 934–934 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 934–934 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 935–935 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 935–935 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 936–936 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 936–936 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 937–937 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 937–937 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 938–938 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 938–938 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 940–942 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 941–941 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 943–945 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 944–944 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 946–948 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 947–947 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 950–950 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 950–950 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 951–951 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 951–951 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 952–954 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 953–953 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 955–955 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 955–955 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 956–956 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 956–956 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 958–960 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 959–959 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 961–963 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 962–962 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 964–964 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 964–964 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 966–966 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 966–966 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 967–967 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 967–967 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 968–970 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 969–969 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 971–973 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 972–972 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 974–974 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 974–974 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 976–978 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 977–977 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 979–981 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 980–980 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 982–982 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 982–982 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 984–984 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 984–984 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 985–985 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 985–985 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 986–986 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 986–986 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 987–987 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 987–987 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 988–988 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 988–988 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 990–992 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 991–991 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 993–995 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 994–994 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 996–998 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 997–997 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 999–999 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 999–999 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1000–1000 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1000–1000 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1001–1001 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1001–1001 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1002–1002 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1002–1002 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1003–1003 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1003–1003 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1005–1007 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1006–1006 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1008–1010 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1009–1009 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1011–1013 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1012–1012 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1015–1015 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1015–1015 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1016–1016 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1016–1016 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1017–1017 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1017–1017 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1019–1021 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1020–1020 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1022–1024 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1023–1023 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1025–1027 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1026–1026 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1029–1029 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1029–1029 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1030–1030 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1030–1030 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1031–1031 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1031–1031 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1033–1035 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1034–1034 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1036–1038 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1037–1037 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1039–1041 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1040–1040 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1044–1044 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1044–1044 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1045–1045 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1045–1045 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1047–1047 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1047–1047 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1048–1050 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1049–1049 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1051–1053 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1052–1052 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1054–1054 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1054–1054 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1055–1057 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1056–1056 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1058–1060 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1059–1059 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1061–1063 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1062–1062 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1065–1065 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1065–1065 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1066–1066 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1066–1066 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1067–1067 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1067–1067 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1068–1068 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1068–1068 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1069–1069 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1069–1069 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1070–1070 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1070–1070 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1071–1071 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1071–1071 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1072–1072 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1072–1072 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1073–1073 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1073–1073 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1074–1074 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1074–1074 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1075–1075 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1075–1075 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1076–1076 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1076–1076 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1077–1077 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1077–1077 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1078–1078 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1078–1078 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1079–1079 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1079–1079 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1080–1080 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1080–1080 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1081–1081 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1081–1081 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1082–1082 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1082–1082 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1086–1086 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1086–1086 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1087–1087 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1087–1087 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1088–1088 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1088–1088 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1089–1089 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1089–1089 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1090–1090 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1090–1090 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1091–1091 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1091–1091 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1093–1093 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1093–1093 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1094–1094 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1094–1094 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1095–1095 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1095–1095 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1096–1096 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1096–1096 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1098–1098 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1098–1098 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1099–1099 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1099–1099 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1101–1101 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1101–1101 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1102–1102 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1102–1102 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1105–1105 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1105–1105 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1106–1106 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1106–1106 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1107–1107 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1107–1107 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1108–1108 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1108–1108 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1109–1109 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1109–1109 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1110–1110 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1110–1110 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1111–1111 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1111–1111 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1112–1112 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1112–1112 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1113–1113 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1113–1113 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1114–1114 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1114–1114 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1116–1116 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1116–1116 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1117–1117 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1117–1117 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1118–1118 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1118–1118 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1119–1119 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1119–1119 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1120–1120 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1120–1120 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1121–1121 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1121–1121 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1122–1122 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1122–1122 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1123–1123 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1123–1123 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1124–1124 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1124–1124 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1125–1125 | __init__ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1125–1125 | __init__ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 1333–4189 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range, np.array, gait.TechCS_Pelvis_Newington, math.TransformAnatCoorSysFromTechCoors, gait.TechCS_Thigh_Newington, math.TransformPointIntoLabCoors, gait.TechCS_Foot_Newington, math.EulerAngles_YXZ, math.EulerAngles_ZXY, T1.dot, T2.dot, T3.dot, gait.AnatCS_Pelvis_Delp, math.RotateCSaroundYaxis, np.eye, math.RotateCSaroundZaxis, math.ComputeMuscleLength, Left_ReFe0.append, Right_ReFe0.append, Left_VaLa0.append, Right_VaLa0.append, math.MassCenter, print, gait.TechCS_Forefoot_mSHCG, gait.TechCS_Trunk_Newington, gait.JointCenterModel_Hip_Newington, gait.JointCenterModel_Hip_Harrington, gait.JointCenterModel_Hip_Harrington2, gait.TechCS_Shank_Newington, gait.JointCenterModel_Ankle_Newington, gait.TechCS_Hindfoot_mSHCG, gait.TechCS_Hallux_mSHCG, gait.AnatCS_Shank_Proximal_Newington, gait.AnatCS_Shank_Distal_VCM, np.cross, np.column_stack, Left_ReFe.append, Right_ReFe.append, Left_GaMe.append, Right_GaMe.append, Left_GaLa.append, Right_GaLa.append, np.matrix, np.linalg.norm, Left_VaLa.append, Right_VaLa.append, np.cos |
| 2005–2005 | __init__ | `[[0.0 for m in range(3)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 2005–2005 | __init__ | `[0.0 for m in range(3)]` | Fully vectorizable allocation / collection | range |
| 2008–2008 | __init__ | `[[0.0 for m in range(3)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 2008–2008 | __init__ | `[0.0 for m in range(3)]` | Fully vectorizable allocation / collection | range |
| 4482–4482 | reArrangeArray | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 4482–4482 | reArrangeArray | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 4483–4486 | reArrangeArray | `for i in range(framecount):` | Partially vectorizable | range |
| 5203–5213 | __init__ | `for fp in [LeftForcePlate_DeviceID, RightForcePlate_DeviceID]:` | Partially vectorizable | SimForcePlate[fp].get('Offset', {}).get, SimForcePlate[fp].get |
| 5545–6460 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range, np.array, int, min, gait.TechCS_Pelvis_Newington, math.TransformAnatCoorSysFromTechCoors, gait.TechCS_Thigh_Newington, gait.TechCS_Foot_Newington, math.TransformVectorIntoMovingCoors, math.TransformVectorIntoLabCoors, np.dot, np.linalg.norm, math.RadiusOfGyration, np.square, gait.TechCS_Shank_Newington, gait.AnatCS_Shank_Proximal_Newington, gait.AnatCS_Shank_Distal_VCM, np.cross, float, np.matrix |
| 5798–5798 | __init__ | `[[0.0 for m in range(3)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 5798–5798 | __init__ | `[0.0 for m in range(3)]` | Fully vectorizable allocation / collection | range |
| 6760–7679 | __init__ | `for FrameNumber in range(StartFrame, EndFrame):` | Partially vectorizable | range, np.array, int, min, gait.TechCS_Pelvis_Newington, math.TransformAnatCoorSysFromTechCoors, gait.TechCS_Thigh_Newington, gait.TechCS_Foot_Newington, math.TransformVectorIntoMovingCoors, math.TransformVectorIntoLabCoors, np.dot, np.linalg.norm, math.RadiusOfGyration, np.square, gait.TechCS_Shank_Newington, gait.AnatCS_Shank_Proximal_Newington, gait.AnatCS_Shank_Distal_VCM, np.cross, float, np.matrix |
| 6993–6993 | __init__ | `[[0.0 for m in range(3)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 6993–6993 | __init__ | `[0.0 for m in range(3)]` | Fully vectorizable allocation / collection | range |

## Py3_GaitModules.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 118–129 | compute_forceplate_valid_zone | `for (fp_key, fp) in fp_data.items():` | Partially vectorizable | fp_data.items, np.asarray, fp.get, np.where, len, int, np.abs |
| 174–175 | _longest_contiguous_valid_window | `for arr in exists_arrays:` | Partially vectorizable | np.asarray |
| 231–242 | _compute_spatial_zone | `for f in range(n_frames):` | Partially vectorizable | range, frames_in_zone.append |
| 291–309 | detect_gait_events | `while len(hs_raw) < 2 and scale >= 0.1:` | Partially vectorizable | max, _logger.info, len, _zeni_detect_gait_events, sorted, trajectory_data.get, set |
| 314–332 | detect_gait_events | `while len(to_raw) < 2 and scale >= 0.1:` | Partially vectorizable | max, _logger.info, len, _zeni_detect_gait_events, sorted, trajectory_data.get, set |
| 352–376 | pair_strike_to_off | `for hs_frame in sorted(hs_frames):` | Partially vectorizable | sorted, paired_events.append, _logger.warning, available_tos.remove, max, min, int |
| 355–359 | pair_strike_to_off | `for to_frame in sorted(available_tos):` | Partially vectorizable | sorted, available_tos.remove |
| 410–414 | apply_zone_filter | `for (frame, label) in events:` | Partially vectorizable | kept.append, dropped.append |
| 429–453 | validate_event_pairing | `for (side_hs, side_of) in [(AUTO_RHS_LABEL, AUTO_ROF_LABEL), (AUTO_LHS_LABEL, AUTO_LOF_LABEL)]:` | Partially vectorizable | side_events.sort, len, _logger.warning |
| 431–431 | validate_event_pairing | `[(f, l) for (f, l) in events if l in (side_hs, side_of)]` | Fully vectorizable allocation / collection |  |
| 434–453 | validate_event_pairing | `while i < len(side_events):` | Partially vectorizable | len, _logger.warning |
| 487–487 | enforce_minimum_detections | `[f for f in current_frames if zone_start <= f <= zone_end]` | Fully vectorizable allocation / collection |  |
| 494–530 | enforce_minimum_detections | `for scale in scales:` | Partially vectorizable | max, print, len, int, _zeni_detect_gait_events, sorted, _logger.warning, trajectory_data.get, set |
| 495–495 | enforce_minimum_detections | `[f for f in current_frames if zone_start <= f <= zone_end]` | Fully vectorizable allocation / collection |  |
| 532–532 | enforce_minimum_detections | `[f for f in current_frames if zone_start <= f <= zone_end]` | Fully vectorizable allocation / collection |  |
| 554–556 | validate_eight_event_sequence | `for (frame, label) in sorted_events:` | Partially vectorizable |  |
| 562–565 | validate_eight_event_sequence | `for i in range(1, len(sorted_events)):` | Partially vectorizable | range, len, consecutive_violations.append |
| 576–576 | validate_eight_event_sequence | `(v != 2 for v in counts.values())` | Fully vectorizable allocation / collection | counts.values |
| 610–613 | remove_false_first_event | `for side in ['R', 'L']:` | Partially vectorizable | all_hs.append |
| 612–613 | remove_false_first_event | `for f in raw[side]['hs']:` | Partially vectorizable | all_hs.append |
| 619–622 | remove_false_first_event | `for side in ['R', 'L']:` | Partially vectorizable | all_events.append |
| 621–622 | remove_false_first_event | `for f in raw[side]['to']:` | Partially vectorizable | all_events.append |
| 665–748 | ensure_strike_before_terminal_off | `for (off_side, strike_side, off_label, strike_label) in [('L', 'R', AUTO_LOF_LABEL, AUTO_RHS_LABEL), ('R', 'L', AUTO_ROF_LABEL, AUTO_LHS_LABEL)]:` | Partially vectorizable | sorted, max, print, _logger.warning, np.asarray, min, all_frames.extend, len, _fp, raw[strike_side]['hs'].append, raw[strike_side]['hs'].sort, _logger.info, int, np.argmax |
| 680–682 | ensure_strike_before_terminal_off | `for s in ['R', 'L']:` | Partially vectorizable | all_frames.extend |
| 687–687 | ensure_strike_before_terminal_off | `[f for f in strikes_same if f < final_off]` | Fully vectorizable allocation / collection |  |
| 691–692 | ensure_strike_before_terminal_off | `[f for f in strikes_opp if last_same_strike < f < final_off]` | Fully vectorizable allocation / collection |  |
| 723–737 | ensure_strike_before_terminal_off | `for prom in [PEAK_PROMINENCE, 1.5, 1.0, 0.5]:` | Partially vectorizable | _fp, len, raw[strike_side]['hs'].append, raw[strike_side]['hs'].sort, print, _logger.info, max, np.argmax, int |
| 786–818 | validate_sequence_order | `for (frame, label) in sorted_events:` | Partially vectorizable | violations.append |
| 826–828 | validate_sequence_order | `for v in violations:` | Partially vectorizable | print, _logger.warning |
| 848–868 | validate_against_ground_truth | `for (gt_frame, gt_label) in ground_truth:` | Partially vectorizable | any, print, _logger.info, min, abs |
| 849–852 | validate_against_ground_truth | `(label == gt_label and abs(frame - gt_frame) <= tolerance_frames for (frame, label) in detected_events)` | Fully vectorizable allocation / collection | abs |
| 858–858 | validate_against_ground_truth | `[(f, l) for (f, l) in detected_events if l == gt_label]` | Fully vectorizable allocation / collection |  |
| 1150–1155 | _get_marker | `for k in fields.keys():` | Partially vectorizable | fields.keys, k.lower, any, isinstance |
| 1152–1152 | _get_marker | `(sub in kl for sub in cand_subs)` | Fully vectorizable allocation / collection |  |
| 1162–1174 | detect_bilateral_gait_events | `for (pair_l, pair_r, pair_name) in [('LPSIS', 'RPSIS', 'PSIS'), ('Left_PSIS', 'Right_PSIS', 'PSIS'), ('LASIS', 'RASIS', 'ASIS'), ('LASI', 'RASI', 'ASI')]:` | Partially vectorizable | _logger.warning, zip |
| 1169–1169 | detect_bilateral_gait_events | `[(l + r) / 2 for (l, r) in zip(lp['X'], rp['X'])]` | Fully vectorizable allocation / collection | zip |
| 1170–1170 | detect_bilateral_gait_events | `[(l + r) / 2 for (l, r) in zip(lp['Y'], rp['Y'])]` | Fully vectorizable allocation / collection | zip |
| 1171–1171 | detect_bilateral_gait_events | `[(l + r) / 2 for (l, r) in zip(lp['Z'], rp['Z'])]` | Fully vectorizable allocation / collection | zip |
| 1172–1172 | detect_bilateral_gait_events | `[a and b for (a, b) in zip(lp['Exists'], rp['Exists'])]` | Fully vectorizable allocation / collection | zip |
| 1252–1255 | detect_bilateral_gait_events | `('Force' in fp and fp['Force'].get('Z') is not None for fp in fp_data.values())` | Fully vectorizable allocation / collection | fp_data.values, fp['Force'].get |
| 1284–1295 | detect_bilateral_gait_events | `for mk in gait_marker_keys:` | Partially vectorizable | marker_names.get, isinstance, all_exists_arrays.append, _get_marker |
| 1298–1301 | detect_bilateral_gait_events | `for pt_label in points_list:` | Partially vectorizable | pt_label.strip, isinstance, all_exists_arrays.append |
| 1337–1348 | detect_bilateral_gait_events | `for (side, heel_key, toe_key) in [('L', 'L_HEEL', 'L_TOE'), ('R', 'R_HEEL', 'R_TOE')]:` | Partially vectorizable | _build_traj, _logger.info, detect_gait_events, _logger.warning |
| 1352–1361 | detect_bilateral_gait_events | `for side in ['R', 'L']:` | Partially vectorizable | enforce_minimum_detections |
| 1364–1366 | detect_bilateral_gait_events | `for (side_code, hs_lbl, to_lbl) in [('R', 'RSTRIKE', 'ROFF'), ('L', 'LSTRIKE', 'LOFF')]:` | Partially vectorizable | _logger.info, len |
| 1368–1370 | detect_bilateral_gait_events | `for (side_code, hs_lbl, to_lbl) in [('R', 'RSTRIKE', 'ROFF'), ('L', 'LSTRIKE', 'LOFF')]:` | Partially vectorizable | print, len |
| 1399–1399 | detect_bilateral_gait_events | `for f in raw['R']['hs']:` | Partially vectorizable | raw_all.append |
| 1400–1400 | detect_bilateral_gait_events | `for f in raw['R']['to']:` | Partially vectorizable | raw_all.append |
| 1401–1401 | detect_bilateral_gait_events | `for f in raw['L']['hs']:` | Partially vectorizable | raw_all.append |
| 1402–1402 | detect_bilateral_gait_events | `for f in raw['L']['to']:` | Partially vectorizable | raw_all.append |
| 1407–1410 | detect_bilateral_gait_events | `for (f, l) in raw_all:` | Partially vectorizable | cleaned_stream.append, abs |
| 1419–1424 | detect_bilateral_gait_events | `for pattern in [p1, p2]:` | Partially vectorizable | range, len, candidates.append |
| 1420–1424 | detect_bilateral_gait_events | `for i in range(len(cleaned_stream) - 7):` | Partially vectorizable | range, len, candidates.append |
| 1422–1422 | detect_bilateral_gait_events | `[x[1] for x in window]` | Fully vectorizable allocation / collection |  |
| 1430–1442 | detect_bilateral_gait_events | `for c in candidates:` | Partially vectorizable | abs, len |
| 1434–1434 | detect_bilateral_gait_events | `[f for (f, l) in c if l == AUTO_LHS_LABEL]` | Fully vectorizable allocation / collection |  |
| 1435–1435 | detect_bilateral_gait_events | `[f for (f, l) in c if l == AUTO_RHS_LABEL]` | Fully vectorizable allocation / collection |  |
| 1450–1460 | detect_bilateral_gait_events | `for (side, hs_label, to_label) in [('R', AUTO_RHS_LABEL, AUTO_ROF_LABEL), ('L', AUTO_LHS_LABEL, AUTO_LOF_LABEL)]:` | Partially vectorizable | pair_strike_to_off, all_paired.extend, list |
| 1456–1456 | detect_bilateral_gait_events | `[f for f in hs_all if zone_start <= f <= zone_end]` | Fully vectorizable allocation / collection |  |
| 1483–1485 | detect_bilateral_gait_events | `for (frame, label) in all_paired:` | Partially vectorizable | events_dict[label].append |
| 1492–1492 | TechCS_Trunk_Newington | `[[0.0 for m in range(3)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 1492–1492 | TechCS_Trunk_Newington | `[0.0 for m in range(3)]` | Fully vectorizable allocation / collection | range |

## Py3_MathModules.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 52–53 | TransformVectorIntoLabCoors | `for i in range(3):` | Partially vectorizable | range |
| 65–66 | TransformVectorIntoMovingCoors | `for i in range(3):` | Partially vectorizable | range |
| 191–191 | AngVelAcc_Euler_YXZ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 191–191 | AngVelAcc_Euler_YXZ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 192–192 | AngVelAcc_Euler_YXZ | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 192–192 | AngVelAcc_Euler_YXZ | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 194–218 | AngVelAcc_Euler_YXZ | `for FrameNumber in range(FirstFrame - 1, LastFrame):` | Partially vectorizable | range, np.cos, np.sin |
| 264–285 | fill_gaps_polynomial | `for i in range(n_dims):` | Partially vectorizable | range, np.polyfit, np.poly1d, p, np.isnan, np.sum, print |
| 293–293 | Differentiate | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 293–293 | Differentiate | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 294–294 | Differentiate | `[[0.0 for m in range(framecount)] for n in range(3)]` | Fully vectorizable allocation / collection | range |
| 294–294 | Differentiate | `[0.0 for m in range(framecount)]` | Fully vectorizable allocation / collection | range |
| 296–337 | Differentiate | `for i in range(3):` | Partially vectorizable | range, np.poly1d, ffit_Polynomial.deriv, FirstDeriv_Polynomial.deriv, FirstDeriv_Polynomial, SecondDeriv_Polynomial, np.all, np.polyfit, np.isfinite |
| 297–337 | Differentiate | `for FrameNumber in range(FirstFrame - 1 + 3, LastFrame - 3):` | Partially vectorizable | range, np.poly1d, ffit_Polynomial.deriv, FirstDeriv_Polynomial.deriv, FirstDeriv_Polynomial, SecondDeriv_Polynomial, np.all, np.polyfit, np.isfinite |
| 344–344 | Smooth1DArray | `[0.0 for m in range(len(DataArray))]` | Fully vectorizable allocation / collection | range, len |
| 350–350 | Smooth1DArray | `[0.0 for m in range(WindowWidth)]` | Fully vectorizable allocation / collection | range |
| 351–351 | Smooth1DArray | `[0.0 for m in range(WindowWidth)]` | Fully vectorizable allocation / collection | range |
| 352–379 | Smooth1DArray | `for FrameNumber in range(StartFrame - 1 + int(WindowWidth / 2), EndFrame - int(WindowWidth / 2)):` | Partially vectorizable | range, np.poly1d, ffit_polynomial, int, np.all, np.polyfit, np.isfinite |
| 353–355 | Smooth1DArray | `for i in range(WindowWidth):` | Partially vectorizable | range, int |
| 370–372 | Smooth1DArray | `for j in range(int(WindowWidth / 2)):` | Partially vectorizable | range, int, ffit_polynomial |
| 377–379 | Smooth1DArray | `for j in range(int(WindowWidth / 2)):` | Partially vectorizable | range, int, ffit_polynomial |
| 385–385 | Smooth3DArray | `[[0.0 for m in range(len(Data3DArray[0]))] for n in range(3)]` | Fully vectorizable allocation / collection | range, len |
| 385–385 | Smooth3DArray | `[0.0 for m in range(len(Data3DArray[0]))]` | Fully vectorizable allocation / collection | range, len |
| 386–386 | Smooth3DArray | `[0.0 for m in range(len(Data3DArray[0]))]` | Fully vectorizable allocation / collection | range, len |
| 387–387 | Smooth3DArray | `[0.0 for m in range(len(Data3DArray[0]))]` | Fully vectorizable allocation / collection | range, len |
| 388–388 | Smooth3DArray | `[0.0 for m in range(len(Data3DArray[0]))]` | Fully vectorizable allocation / collection | range, len |
| 391–394 | Smooth3DArray | `for i in range(len(Data3DArray[0])):` | Partially vectorizable | range, len |
| 399–402 | Smooth3DArray | `for i in range(len(Data3DArray[0])):` | Partially vectorizable | range, len |
| 407–407 | Trim3DList | `[[0.0 for m in range(EndFrame - StartFrame + 1)] for n in range(len(List))]` | Fully vectorizable allocation / collection | range, len |
| 407–407 | Trim3DList | `[0.0 for m in range(EndFrame - StartFrame + 1)]` | Fully vectorizable allocation / collection | range |
| 408–410 | Trim3DList | `for i in range(len(List)):` | Partially vectorizable | range, len |
| 409–410 | Trim3DList | `for j in range(StartFrame - 1, EndFrame):` | Partially vectorizable | range |
| 416–455 | ComputeMuscleLength | `for i in range(len(MusclePoints) - 1):` | Partially vectorizable | range, len, TransformPointIntoLabCoors, MusclePointsLab.append, np.linalg.norm |

## Py3_CreateGCD.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 100–102 | __init__ | `for measurement_name in measurement_names:` | Partially vectorizable | float, setattr, getattr, abs |
| 153–155 | __init__ | `for i in range(len(LeftFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 156–158 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 159–161 | __init__ | `for i in range(len(RightFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 162–164 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 168–168 | ComputeGCDVariable | `[0 for m in range(Strike2 - Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 169–169 | ComputeGCDVariable | `[0 for m in range(Strike2 - Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 170–170 | ComputeGCDVariable | `[0 for m in range(Strike2 - Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 197–202 | ComputeGCDVariableEMG | `for ID in EMG_DigitalDeviceOutputIDs:` | Partially vectorizable | vicon.GetDeviceOutputDetails |
| 208–208 | ComputeGCDVariableEMG | `[0 for m in range(EMGFrame_Strike2 - EMGFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 209–210 | ComputeGCDVariableEMG | `for i in range(EMGFrame_Strike1 - 1, EMGFrame_Strike2):` | Partially vectorizable | range |
| 212–212 | ComputeGCDVariableEMG | `[0 for m in range(Strike2 - Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 235–235 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 236–236 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 237–237 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 238–238 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 239–239 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 240–240 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 243–254 | ComputeGCDVariableFP_Component | `for i in range(FPFrame_Strike1 - 1, FPFrame_Strike2):` | Partially vectorizable | range, print |
| 268–268 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 269–269 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 270–270 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 271–271 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 272–272 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 273–273 | ComputeGCDVariableFP_Component | `[0 for m in range(FPFrame_Strike2 - FPFrame_Strike1 + 1)]` | Fully vectorizable allocation / collection | range |
| 289–290 | WriteArrayToGCD | `for i in range(len(GCDVariable)):` | Partially vectorizable | range, len, GCDFile.write, str, np.format_float_positional, float |
| 299–300 | WriteArrayToGCD_ComputeEMGenvelope | `for i in range(len(GCDVariable)):` | Partially vectorizable | range, len, GCDFile.write, str, round, float |
| 309–326 | WriteArrayToGCD_ComputeEMGenvelope | `for DeviceID in DeviceIDs:` | Partially vectorizable | vicon.GetDeviceDetails, vicon.GetDeviceOutputDetails, len |
| 333–337 | WriteArrayToGCD_ComputeEMGenvelope | `for ID in EMG_DeviceOutputIDs:` | Partially vectorizable | vicon.GetDeviceOutputDetails |
| 366–372 | WriteArrayToGCD_ComputeEMGenvelope | `for i in range(len(GCDVariable_Rectified)):` | Partially vectorizable | range, len, sum, int |
| 378–379 | WriteArrayToGCD_ComputeEMGenvelope | `for i in range(len(GCDVariable_Envelope)):` | Partially vectorizable | range, len, GCDFile.write, str, round, float |
| 423–461 | __init__ | `for numCycle in range(len(LeftFootStrikeEventFrames) - 1):` | Partially vectorizable | range, tk.Radiobutton, numCycleButton.place, len, sorted, str, tk.Label, WarningLabel.place, ReadCycleSelectionLeft |
| 431–433 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 434–436 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 437–439 | __init__ | `for i in range(len(RightFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 479–481 | ReadCycleSelectionLeft | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 482–484 | ReadCycleSelectionLeft | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 485–487 | ReadCycleSelectionLeft | `for i in range(len(RightFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 505–507 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 508–510 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 511–513 | __init__ | `for i in range(len(RightFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 521–523 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 524–526 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 527–529 | __init__ | `for i in range(len(RightFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 696–715 | __init__ | `for DeviceID in DeviceIDs:` | Partially vectorizable | vicon.GetDeviceDetails, vicon.GetDeviceOutputDetails, len |
| 796–834 | __init__ | `for numCycle in range(len(RightFootStrikeEventFrames) - 1):` | Partially vectorizable | range, tk.Radiobutton, numCycleButton.place, len, sorted, str, tk.Label, WarningLabel.place, ReadCycleSelectionRight |
| 804–806 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 807–809 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 810–812 | __init__ | `for i in range(len(LeftFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 857–859 | ReadCycleSelectionRight | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 860–862 | ReadCycleSelectionRight | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 863–865 | ReadCycleSelectionRight | `for i in range(len(LeftFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 882–884 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 885–887 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 888–890 | __init__ | `for i in range(len(LeftFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 897–899 | __init__ | `for i in range(len(RightFootOffEventFrames)):` | Partially vectorizable | range, len |
| 900–902 | __init__ | `for i in range(len(LeftFootOffEventFrames)):` | Partially vectorizable | range, len |
| 903–905 | __init__ | `for i in range(len(LeftFootStrikeEventFrames)):` | Partially vectorizable | range, len |
| 1066–1085 | __init__ | `for DeviceID in DeviceIDs:` | Partially vectorizable | vicon.GetDeviceDetails, vicon.GetDeviceOutputDetails, len |

## Py3_varExtractor.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 51–51 | extract_c3d | `[60.0 * m + sec for (m, sec) in zip(evt_times[0], evt_times[1])]` | Fully vectorizable allocation / collection | zip |
| 54–58 | extract_c3d | `[(60.0 * minutes + seconds) * fields['Capture_Frequency'] - round((60.0 * minutes + seconds) * fields['Capture_Frequency']) for (minutes, seconds) in zip(evt_times[0], evt_times[1])]` | Fully vectorizable allocation / collection | round, zip |
| 72–76 | extract_c3d | `for (label, frame, off, context) in zip(evt_label, evt_frames, evt_offsets, evt_contexts):` | Partially vectorizable | zip, tmp[ctx_map.get(context, {}).get(label, label)]['FrameNo'].append, tmp[ctx_map.get(context, {}).get(label, label)]['EventOffset'].append, ctx_map.get(context, {}).get, ctx_map.get |
| 80–82 | extract_c3d | `for (label, frame, off) in zip(evt_label, evt_frames, evt_offsets):` | Partially vectorizable | zip, tmp[label]['FrameNo'].append, tmp[label]['EventOffset'].append |
| 101–104 | extract_c3d | `for p in json_candidates:` | Partially vectorizable | os.path.isfile |
| 116–129 | extract_c3d | `for ev in loaded_events:` | Partially vectorizable | ev.get, tmp_json[lbl]['FrameNo'].append, tmp_json[lbl]['EventOffset'].append, all_ev_frames.append, int |
| 200–223 | extract_c3d | `for (key, val) in processing.items():` | Partially vectorizable | processing.items, print, isinstance, len, value.isdigit, abs |
| 236–247 | extract_c3d | `for (inx, val) in enumerate(fields['Points']):` | Partially vectorizable | enumerate, val.strip, range, np.isnan, len |
| 240–241 | extract_c3d | `for (i, channel) in enumerate(channels):` | Partially vectorizable | enumerate |
| 242–247 | extract_c3d | `[not (np.isnan(fields[val]['X'][j]) or np.isnan(fields[val]['Y'][j]) or np.isnan(fields[val]['Z'][j])) for j in range(len(fields[val]['X']))]` | Fully vectorizable allocation / collection | range, np.isnan, len |
| 271–307 | extract_fields_by_filename | `for measurement in root.findall('.//Measurement'):` | Partially vectorizable | root.findall, measurement.get, os.path.join, measurement.get('Filename').split, os.path.dirname, extract_c3d, filename_attr.split |
| 337–338 | <module> | `for (key, value) in list(fields.items()):` | Partially vectorizable | list, fields.items, print |

## Py3_Utils.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 87–88 | CreateModelOutput | `for componentName in componentNames:` | Partially vectorizable |  |
| 110–116 | SetModelOutput | `for (key, val) in self.model.items():` | Partially vectorizable | self.model.items, zip |
| 112–115 | SetModelOutput | `for (componentName, value) in zip(val[modelOutputName]['Name'], components):` | Partially vectorizable | zip |
| 120–125 | GetModelOutput | `for i in self.model.keys():` | Partially vectorizable | self.model.keys, arr.append, len |
| 122–123 | GetModelOutput | `for componentName in self.model[i][ModelName]['Name']:` | Partially vectorizable | arr.append |
| 131–136 | printItem | `for (key, val) in self.model.items():` | Partially vectorizable | self.model.items, print, val[name].items |
| 134–135 | printItem | `for (componentName, value) in val[name].items():` | Partially vectorizable | val[name].items, print |
| 152–153 | __init__ | `for font_file in fonts_dir.glob('*.ttf'):` | Partially vectorizable | fonts_dir.glob, QFontDatabase.addApplicationFont, str |
| 309–310 | _create_widgets | `for plate_id in self.payload:` | Partially vectorizable | self._create_plate_widget |
| 333–337 | _create_center_mod | `for (i, h) in enumerate(headers):` | Partially vectorizable | enumerate, QLabel, lbl.setFont, lbl.setStyleSheet, config_grid.addWidget, QFont |
| 350–355 | create_input_row | `for (i, val) in enumerate(vals):` | Partially vectorizable | enumerate, QLineEdit, e.setAlignment, e.setMaximumWidth, config_grid.addWidget, entries.append |
| 361–362 | create_input_row | `for e in entries:` | Partially vectorizable | e.editingFinished.connect |
| 379–379 | update_offset | `[float(val) for val in values]` | Fully vectorizable allocation / collection | float |
| 394–394 | update_origin | `[float(val) for val in values]` | Fully vectorizable allocation / collection | float |
| 407–407 | update_world_center | `[float(val) for val in values]` | Fully vectorizable allocation / collection | float |
| 451–455 | _create_plate_widget | `for (i, h) in enumerate(headers):` | Partially vectorizable | enumerate, QLabel, lbl.setFont, lbl.setStyleSheet, stats_grid.addWidget, QFont |
| 458–472 | _create_plate_widget | `for data_type in ['Force', 'Moment', 'Center_of_Pressure']:` | Partially vectorizable | QLabel, type_lbl.setStyleSheet, stats_grid.addWidget, enumerate, data_type.replace, self.calculate_max_min, val_lbl.setFont, val_lbl.setStyleSheet, val_lbl.setAlignment, QFont |
| 462–471 | _create_plate_widget | `for (col, axis) in enumerate(['X', 'Y', 'Z']):` | Partially vectorizable | enumerate, self.calculate_max_min, QLabel, val_lbl.setFont, val_lbl.setStyleSheet, val_lbl.setAlignment, stats_grid.addWidget, QFont |
| 489–493 | on_left_selected | `for (other_id, other_cb) in self._left_checkboxes.items():` | Partially vectorizable | self._left_checkboxes.items, other_cb.isChecked, other_cb.blockSignals, other_cb.setChecked |
| 511–515 | on_right_selected | `for (other_id, other_cb) in self._right_checkboxes.items():` | Partially vectorizable | self._right_checkboxes.items, other_cb.isChecked, other_cb.blockSignals, other_cb.setChecked |
| 584–639 | ProcessForceplateData | `for id in range(n):` | Partially vectorizable | range, len, np.mean, normalize_zeroes, tmp[str(qid)].get, np.array, str, align_to_c3d, np.round |

## gapi.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 89–90 | SetTrajectory | `for (key, values) in (('X', X), ('Y', Y), ('Z', Z)):` | Partially vectorizable | float |
| 90–90 | SetTrajectory | `[float(v) if v is not None else None for v in values]` | Fully vectorizable allocation / collection | float |
| 91–91 | SetTrajectory | `[bool(v) for v in exists]` | Fully vectorizable allocation / collection | bool |
| 152–155 | SetEvents | `for (label, frame_list) in events_dict.items():` | Partially vectorizable | events_dict.items, frame_to_time, bulk_events.append, int |
| 153–155 | SetEvents | `for frame_no in frame_list:` | Partially vectorizable | frame_to_time, bulk_events.append, int |
| 239–241 | <module> | `while True:` | Partially vectorizable | getProjDirectory, time.sleep |

## processing_service.py

| Lines | Function | Loop | Classification | Calls |
|---|---|---|---|---|
| 41–43 | _resolve_python_launcher | `for c in candidates:` | Partially vectorizable | c.is_file, str |
| 131–166 | run | `for line in iter(self._process.stdout.readline, ''):` | Partially vectorizable | iter, line.rstrip, stdout_lines.append, self.log_line.emit, re.search, min, self.progress.emit, int, m.group, line_clean.strip, st_pcts.get, max, m_st.group |
