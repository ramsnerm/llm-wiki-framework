# tests/

Behavioural cases: a prompt is sent to a real agent in a throwaway
directory, and the files it leaves behind are checked mechanically.

```
python3 tests/run.py --list
python3 tests/run.py --case ingest-source --model claude
```

How the suite is built, what each case covers, how to add one, and the
safety rules the runs depend on: [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).
