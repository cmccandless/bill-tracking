# bill-tracking

1. Fill out new budget.yml. Example:
```YAML
paycheck: 1200

bills:
- name: Rent
  amount: 600
- name: HelloFresh
  amount: 51.92
  cycle: weekly
  weekday: 0  # Monday
- name: Disney+
  cycle: yearly
  month: 1
  day: 25
```

2. `./bill_tracker.py 2021/01/08 1234.56`
