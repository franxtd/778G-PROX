import pathlib, shutil, subprocess, sys
installed, dest, manifests, logs = map(pathlib.Path, sys.argv[1:])
modules = {}
for p in sorted(installed.rglob("*.ko")):
    if p.name in modules:
        raise SystemExit(f"Duplicate module: {p.name}")
    modules[p.name] = p
if not modules:
    raise SystemExit("No installed modules")
report = []
def stage(name, rel, selected, manifest):
    output = dest / name / rel
    output.mkdir(parents=True, exist_ok=True)
    requested = (manifests / manifest).read_text().splitlines()
    requested = [x.strip() for x in requested if x.strip() and not x.startswith("#")]
    missing = [x for x in requested if x not in selected]
    report.append(f"{name}: {len(selected)} modules; missing requested: {missing}")
    for module in selected:
        shutil.copy2(modules[module], output / module)
    base = dest / ("depmod-" + name)
    staging = base / "lib/modules/0.0" / rel
    staging.mkdir(parents=True, exist_ok=True)
    for module in selected:
        shutil.copy2(modules[module], staging / module)
    subprocess.run(["depmod", "-b", str(base.resolve()), "0.0"], check=True)
    metadata = base / "lib/modules/0.0"
    for filename in ("modules.alias", "modules.softdep"):
        shutil.copy2(metadata / filename, output / filename)
    dep = (metadata / "modules.dep").read_text()
    (output / "modules.dep").write_text("\n".join(" ".join(("/" + t if t and not t.startswith("/") else t) for t in line.split()) for line in dep.splitlines()) + "\n")
    (output / "modules.load").write_text("".join(pathlib.Path(x).stem + "\n" for x in requested if x in selected))
    shutil.rmtree(base)
stage("vendor", pathlib.Path("vendor/lib/modules"), set(modules), "modules.load")
boot = {x.strip() for x in (manifests / "modules.load.recovery").read_text().splitlines() if x.strip()}
stage("vendor-ramdisk", pathlib.Path("lib/modules"), boot.intersection(modules), "modules.load.recovery")
(logs / "rom-module-staging-report.txt").write_text("\n".join(report) + "\n")
print("\n".join(report))
