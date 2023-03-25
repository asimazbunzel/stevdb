- [x] update the way in which we check for new simulations once the first big loop has finished.
This is important when, for example, the final location of the simulations matches their original
directory (should be with some list inside the MESAbinaryGrid class)

- [x] change `evolution(s)`, `run(s)` and `simulation(s)` for `model(s)` as the MESA code produces
stellar-evolution models

- [x] change `folder(s)` for `directory(ies)`

- [ ] implement method to look for final conditions on database of a MESA run, based on its id.
Check if it will be replaced or skipped

- [ ] change code flow in `run1_summary` to skip writing the same thing twice (or even more)
