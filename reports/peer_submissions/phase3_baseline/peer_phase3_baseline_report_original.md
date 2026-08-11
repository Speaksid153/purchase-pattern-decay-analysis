======================================================================
NUMERIC FEATURE INSIGHTS
======================================================================

--- base_user_tenure_days ---
count:  2,593,914
mean:   146.00
median: 131.00
std:    87.76
min:    2.00
25%:    73.00
75%:    210.00
max:    365.00

--- base_total_orders_to_date ---
count:  2,593,914
mean:   20.80
median: 15.00
std:    17.99
min:    4.00
25%:    8.00
75%:    28.00
max:    99.00

--- base_avg_days_between_orders ---
count:  2,593,914
mean:   10.06
median: 8.60
std:    5.73
min:    0.50
25%:    5.80
75%:    13.20
max:    30.00
NOTE: max hits the dataset's 30-day cap — some values may be distorted for irregular/long-gap users.

--- base_avg_basket_size_to_date ---
count:  2,593,914
mean:   10.08
median: 9.08
std:    5.68
min:    1.00
25%:    6.05
75%:    13.00
max:    73.50

--- base_avg_reorder_ratio_to_date ---
count:  2,593,914
mean:   0.54
median: 0.56
std:    0.20
min:    0.00
25%:    0.40
75%:    0.69
max:    0.99

======================================================================
CATEGORICAL FEATURE INSIGHTS
======================================================================

--- base_order_dow ---
                 count   pct
base_order_dow              
0               443625  17.1
1               450314  17.4
2               357501  13.8
3               334719  12.9
4               327045  12.6
5               346972  13.4
6               333738  12.9
Most common value: 1 (17.4% of snapshots)

--- base_order_hour ---
                  count  pct
base_order_hour             
0                 16988  0.7
1                  9089  0.4
2                  5591  0.2
3                  4066  0.2
4                  4132  0.2
5                  7326  0.3
6                 23918  0.9
7                 72222  2.8
8                139703  5.4
9                200547  7.7
10               222039  8.6
11               216875  8.4
12               205476  7.9
13               210225  8.1
14               213799  8.2
15               213718  8.2
16               204689  7.9
17               170261  6.6
18               135308  5.2
19               104270  4.0
20                78344  3.0
21                59168  2.3
22                46068  1.8
23                30092  1.2
Most common value: 10 (8.6% of snapshots)

- Median user tenure at time of snapshot is 131 days (mean 146), with the middle 50% between 73-210 days — most eligible snapshots come from users who've been active for several months, consistent with requiring 3+ historical orders to even qualify.
- Median order_number (sequence position) at snapshot is 15 (mean 20.8), ranging up to 99 — confirms the eligible population skews toward established, higher-frequency users, not just-qualified ones.
- Median avg basket size is 9.08 items (mean 10.08), middle 50% between 6.05-13 items 
- Median avg reorder ratio is 0.56 (mean 0.54) 
- Median avg days between orders is 8.6 (mean 10.06), max exactly 30 — confirms the 30-day cap directly affects this feature
- Order hour shows a clear daytime shopping pattern: volume ramps up from 6am, peaks between 9am-4pm (each hour ~7.5-8.6% of snapshots), and tapers sharply after 6pm — very few orders placed overnight (12am-5am, each under 1%).
- Minimum tenure observed is just 2 days despite requiring 3+ historical orders — implies some users placed multiple orders within a very short span 