git worktree add ../wt-zaehlen -b feat/zaehlen
cd ../wt-zaehlen
git rev-parse --git-path hooks/pre-commit   # muss githooks/pre-commit zeigen
