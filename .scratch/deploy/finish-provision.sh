#!/bin/sh
set -eu
cd /opt/bozhou-practice
docker volume create bozhou-practice_database >/dev/null
docker run --rm --user 0 --entrypoint python \
  -v bozhou-practice_database:/data \
  -v /root/practice-migration.db:/migration.db:ro \
  bozhou-practice:current -c 'import pathlib,shutil,os,sqlite3; p=pathlib.Path("/data/practice.db"); assert not p.exists(), "Target database already exists"; shutil.copyfile("/migration.db",p); os.chown(p,10001,10001); os.chmod(p,0o600); c=sqlite3.connect(p); assert c.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; print("Migrated accounts:",c.execute("SELECT count(*) FROM users").fetchone()[0]); c.close()'
docker compose -f compose.server.yaml up -d --no-build practice backup
for attempt in $(seq 1 40); do
  health=$(docker inspect bozhou-practice-practice-1 --format '{{.State.Health.Status}}')
  if [ "$health" = healthy ]; then
    docker compose -f compose.server.yaml ps
    exit 0
  fi
  sleep 3
done
docker compose -f compose.server.yaml logs --tail=40 practice
echo 'New app not healthy; old quiz route remains unchanged.' >&2
exit 1
