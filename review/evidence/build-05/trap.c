int chk(int *p, int n) { if (!p) __builtin_trap(); int s = 0; for (int i = 0; i < n; i++) s += p[i] * 3; return s; }
