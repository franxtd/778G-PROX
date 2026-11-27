#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Read-only capability probe, plus explicitly requested bounded ETM recording.
set -eu
umask 077
mode=${1:-probe}
base=${2:-/data/local/tmp/fran-autofdo}
case "$mode" in probe|record) ;; *) echo 'usage: device.sh probe|record [output-directory] [seconds]'; exit 2;; esac
[ "$(id -u)" = 0 ] || { echo 'Execute como root com su -c.'; exit 1; }
mkdir -p "$base"
case "$base" in /*) ;; *) echo 'Use um diretório absoluto.'; exit 2;; esac
report="$base/probe.txt"
sources=0
{
  echo 'FRAN_AUTOFDO_PROBE v1'
  cat /proc/version
  for key in ro.product.device ro.build.version.release ro.build.fingerprint; do
    printf '%s=' "$key"; getprop "$key"
  done
  echo '--- PERF PMUs ---'
  for d in /sys/bus/event_source/devices/*; do
    [ -r "$d/type" ] || continue
    printf '%s type=' "${d##*/}"; cat "$d/type"
  done
  echo '--- CoreSight CPU ETM sources ---'
  for d in /sys/bus/coresight/devices/*; do
    [ -d "$d" ] || continue
    name=${d##*/}
    case "$name" in *etm*)
      printf '%s driver=' "$name"
      readlink "$d/driver" || true
      for f in cpu mgmt/trcauthstatus; do
        if [ -r "$d/$f" ]; then printf '%s=' "$f"; cat "$d/$f" || true; fi
      done
      ;;
    esac
  done
  echo '--- Kernel config ---'
  if [ -r /proc/config.gz ]; then
    zcat /proc/config.gz | grep -E '^(# )?CONFIG_(AUTOFDO_CLANG|CORESIGHT_SOURCE_ETM4X|PID_IN_CONTEXTIDR|PERF_EVENTS|THINLTO|CFI_CLANG|DEBUG_INFO)(=| )' || true
  fi
  echo '--- simpleperf ---'
  if command -v simpleperf >/dev/null 2>&1; then simpleperf --version 2>&1 || true; else echo 'simpleperf ausente'; fi
} > "$report" 2>&1
cat "$report"
echo "Relatório: $report"
[ "$mode" = record ] || exit 0

seconds=${3:-15}
case "$seconds" in ''|*[!0-9]*) echo 'Duração inválida.'; exit 2;; esac
[ "$seconds" -ge 5 ] && [ "$seconds" -le 60 ] || { echo 'Use de 5 a 60 segundos.'; exit 2; }
command -v simpleperf >/dev/null 2>&1 || { echo 'Instale um simpleperf oficial compatível antes de coletar.'; exit 1; }
[ -r /sys/bus/event_source/devices/cs_etm/type ] || { echo 'PMU cs_etm indisponível; AutoFDO ainda não pode ser coletado.'; exit 1; }
for d in /sys/bus/coresight/devices/*; do
  [ -r "$d/cpu" ] && [ -L "$d/driver" ] && [ -r "$d/mgmt/trcauthstatus" ] || continue
  sources=$((sources+1))
done
[ "$sources" -gt 0 ] || { echo 'Nenhuma fonte ETM de CPU registrada. Ter o PMU cs_etm sozinho não basta.'; exit 1; }
[ -r /sys/kernel/notes ] || { echo 'Sem identidade de build em /sys/kernel/notes.'; exit 1; }
run="$base/trace-$(date +%Y%m%d-%H%M%S)-$$"
mkdir "$run"
cp /sys/kernel/notes "$run/kernel.notes"
cat /proc/version > "$run/proc-version.txt"
cp "$report" "$run/probe.txt"
echo "Coletando kernel por $seconds segundos. Execute a carga desejada no aparelho."
if ! simpleperf record -e cs-etm:k -a --duration "$seconds" -z -o "$run/perf.data" > "$run/record.log" 2>&1; then
  cat "$run/record.log"; echo "Coleta falhou: $run"; exit 1
fi
if ! simpleperf inject -i "$run/perf.data" --output branch-list --binary kernel.kallsyms -o "$run/branch.data" > "$run/inject.log" 2>&1; then
  cat "$run/inject.log"; echo "Conversão falhou: $run"; exit 1
fi
[ -s "$run/branch.data" ] || { echo 'Coleta vazia: não usar como perfil.'; exit 1; }
sha256sum "$run/kernel.notes" "$run/perf.data" "$run/branch.data" > "$run/SHA256SUMS.txt"
echo "Coleta: $run"
echo 'Preserve os arquivos e os símbolos vmlinux do MESMO build. Ainda não há perfil otimizado.'
