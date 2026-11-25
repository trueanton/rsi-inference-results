# Variation across timed repetitions

Each row describes one arm of one public benchmark pass on two A100s. Decode uses each repetition’s median time per output token (TPOT). Prefill uses each repetition’s median time to first token (TTFT). High load uses each profile’s completed requests per second. The combined high-load row takes the geometric mean across the three concurrencies within each repetition before summarizing across repetitions.

The mean, minimum, maximum and sample standard deviation (SD, denominator n − 1) use all repetitions, before score trimming. Values are rounded to five decimal places. A single observation gives no estimate of between-repetition variation. Two decode boots or two high-load repetitions provide only one degree of freedom. These samples describe this run on this device pair. They cannot establish campaign-to-campaign variation or a general noise floor.

## GPT-OSS-120B · qualification

[Per-repetition CSV](../../tasks/optimize_gpt_oss_120b_2xh100_open/results/raw-measurements.csv)

| Metric | Unit | Arm | n | Mean | Min | Max | Sample SD |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Decode TPOT | ms/token | candidate | 2 | 6.10837 | 6.10825 | 6.10849 | 0.00017 |
| Decode TPOT | ms/token | pristine | 2 | 6.10843 | 6.10760 | 6.10925 | 0.00117 |
| Prefill TTFT | ms | candidate | 5 | 644.48617 | 644.26603 | 644.92668 | 0.25827 |
| Prefill TTFT | ms | pristine | 5 | 646.84766 | 646.02129 | 648.04467 | 0.88104 |
| High load c16 | requests/s | candidate | 2 | 1.14167 | 1.13886 | 1.14449 | 0.00398 |
| High load c16 | requests/s | pristine | 2 | 1.14151 | 1.13520 | 1.14782 | 0.00892 |
| High load c32 | requests/s | candidate | 2 | 1.50098 | 1.49853 | 1.50343 | 0.00346 |
| High load c32 | requests/s | pristine | 2 | 1.50293 | 1.49640 | 1.50947 | 0.00924 |
| High load c64 | requests/s | candidate | 2 | 1.49183 | 1.49121 | 1.49244 | 0.00087 |
| High load c64 | requests/s | pristine | 2 | 1.50617 | 1.49360 | 1.51874 | 0.01778 |
| High load combined | requests/s | candidate | 2 | 1.36735 | 1.36567 | 1.36902 | 0.00237 |
| High load combined | requests/s | pristine | 2 | 1.37222 | 1.36894 | 1.37550 | 0.00464 |

## GPT-OSS-120B · additional profiling during the solver attempt

[Per-repetition CSV](../../tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-profiling/raw-measurements.csv)

| Metric | Unit | Arm | n | Mean | Min | Max | Sample SD |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Decode TPOT | ms/token | candidate | 2 | 6.12491 | 6.12484 | 6.12499 | 0.00011 |
| Decode TPOT | ms/token | pristine | 2 | 6.12499 | 6.12429 | 6.12569 | 0.00099 |
| Prefill TTFT | ms | candidate | 5 | 645.29692 | 644.42777 | 647.92286 | 1.48179 |
| Prefill TTFT | ms | pristine | 5 | 646.63837 | 646.12890 | 647.12583 | 0.35463 |
| High load c16 | requests/s | candidate | 2 | 1.15217 | 1.14838 | 1.15597 | 0.00536 |
| High load c16 | requests/s | pristine | 2 | 1.14008 | 1.13593 | 1.14423 | 0.00587 |
| High load c32 | requests/s | candidate | 2 | 1.51902 | 1.51253 | 1.52552 | 0.00919 |
| High load c32 | requests/s | pristine | 2 | 1.51335 | 1.51291 | 1.51379 | 0.00063 |
| High load c64 | requests/s | candidate | 2 | 1.49176 | 1.48641 | 1.49710 | 0.00756 |
| High load c64 | requests/s | pristine | 2 | 1.50653 | 1.50242 | 1.51065 | 0.00582 |
| High load combined | requests/s | candidate | 2 | 1.37697 | 1.37578 | 1.37816 | 0.00169 |
| High load combined | requests/s | pristine | 2 | 1.37494 | 1.37466 | 1.37522 | 0.00040 |

## Qwen3.6-27B · qualification

[Per-repetition CSV](../../tasks/optimize_qwen3_6_27b_1xh100_open/results/raw-measurements.csv)

| Metric | Unit | Arm | n | Mean | Min | Max | Sample SD |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Decode TPOT | ms/token | candidate | 1 | 23.77341 | 23.77341 | 23.77341 | N/A |
| Decode TPOT | ms/token | pristine | 1 | 23.76841 | 23.76841 | 23.76841 | N/A |
| Prefill TTFT | ms | candidate | 5 | 1203.78303 | 1203.55365 | 1203.99093 | 0.18495 |
| Prefill TTFT | ms | pristine | 5 | 1203.74192 | 1202.80550 | 1205.10760 | 0.99035 |
| High load c16 | requests/s | candidate | 1 | 0.51993 | 0.51993 | 0.51993 | N/A |
| High load c16 | requests/s | pristine | 1 | 0.52002 | 0.52002 | 0.52002 | N/A |
| High load c32 | requests/s | candidate | 1 | 0.87164 | 0.87164 | 0.87164 | N/A |
| High load c32 | requests/s | pristine | 1 | 0.87159 | 0.87159 | 0.87159 | N/A |
| High load c64 | requests/s | candidate | 1 | 1.10916 | 1.10916 | 1.10916 | N/A |
| High load c64 | requests/s | pristine | 1 | 1.10959 | 1.10959 | 1.10959 | N/A |
| High load combined | requests/s | candidate | 1 | 0.79511 | 0.79511 | 0.79511 | N/A |
| High load combined | requests/s | pristine | 1 | 0.79524 | 0.79524 | 0.79524 | N/A |
