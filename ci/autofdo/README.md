# AutoFDO — backport de compilação para FranBakaSU 5.4 / Dubai LOS21

Este projeto adiciona suporte de build, metadados para coleta e validação de
perfis. O build **collect/PREPARE não aplica um perfil e não é um kernel já
otimizado por AutoFDO**. Sem dados reais do aparelho não há ganho medido.

## O que foi integrado

* CONFIG_AUTOFDO_CLANG, baseado no Android common 6.6 e adaptado ao
  CONFIG_THINLTO desta árvore 5.4, com Clang 23 fixado no workflow.
* Discriminadores e informação de debug para associar amostras ao código.
* CLANG_AUTOFDO_PROFILE para o compilador e o backend ThinLTO do vmlinux.
* Módulos, vDSO e stub EFI fora do perfil. Dependências de arquivo garantem
  recompilação quando o perfil muda, mesmo conservando o nome.
* Teste real do roteamento de flags do Kbuild e teste LLVM/ThinLTO/CFI com
  um perfil sintético restrito a um pequeno programa de teste. Esse perfil
  nunca é usado no kernel entregue.
* Bundle do vmlinux com debug, build ID, kernel.notes, configuração e hashes.
* Conversão ETM e validação de identidade do binário, perfil não vazio,
  código do kernel, configuração e revisão do compilador.
* WALT, correção process_madvise, prioridade da fila de GPU, BakaSU, SUSFS,
  NoMount e FAS da revisão eb1abf13 preservados.

## Primeiro passo no aparelho: diagnóstico

Não precisa instalar outro kernel para executar este diagnóstico. Copie
device.sh para /data/local/tmp/fran-autofdo-device.sh e execute:

```sh
su -c 'sh /data/local/tmp/fran-autofdo-device.sh probe'
```

O relatório fica em /data/local/tmp/fran-autofdo/probe.txt. A árvore atual
tem CoreSight, mas CONFIG_CORESIGHT_SOURCE_ETM4X está desativado. O PMU
cs_etm pode aparecer mesmo sem fontes ETM de CPU registradas; sua presença
sozinha não comprova capacidade de coleta. O diagnóstico também mostra
os drivers, autorização de trace e a disponibilidade do simpleperf.

O suporte de coleta do SoC/bootloader precisa ser confirmado antes de ativar
drivers de trace. Este backport não muda fusíveis, firmware, DTB, SELinux,
permissões globais de perf ou os drivers ETM. O kernel PREPARE, portanto,
não resolve sozinho a indisponibilidade de ETM no aparelho.

## Coleta quando ETM estiver disponível

Use um simpleperf oficial com suporte a ETM e o kernel correspondente ao
bundle de símbolos guardado. Rode uma carga representativa: jogos usados,
abertura de apps e multitarefa. Para uma coleta curta:

```sh
su -c 'sh /data/local/tmp/fran-autofdo-device.sh record /data/local/tmp/fran-autofdo 15'
```

A coleta é explícita, temporária e não instala serviço. Ela consome CPU e
armazenamento; não use o FPS observado durante a coleta como benchmark.
Falhas de fonte, acesso ou gravação são reportadas e não geram um perfil
falso. Preserve o diretório trace-* e o bundle de símbolos do MESMO build.

## Conversão no computador

Instale as ferramentas oficiais simpleperf (host), create_llvm_prof do
projeto google/autofdo e llvm-profdata compatível. A conversão usa o fluxo
ETM documentado pelo AOSP e não ignora divergências de build ID.

```sh
python3 ci/autofdo/profile.py convert trace-dir symbols-dir kernel.afdo
```

O comando produz kernel.afdo e kernel.afdo.json. A saída deve conter amostras
reais e corresponder ao código e à configuração do build de destino. Perfis
genéricos de GKI 6.6/6.12 não são fornecidos como perfil deste kernel 5.4.

## Recompilar usando um perfil real

Depois de gerar a configuração com AUTOFDO_CLANG=y, valide e compile:

```sh
python3 ci/autofdo/profile.py validate /caminho/kernel.afdo out/.config
make O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 \
  CLANG_AUTOFDO_PROFILE=/caminho/kernel.afdo Image dtbs modules
```

Use também as mesmas opções e ferramentas do workflow fixado no repositório.
No Actions, workflow_dispatch oferece collect, off e profile. Para profile,
adicione o perfil e seu JSON em ci/autofdo/profiles/ no branch e indique o
caminho relativo; essa entrada é validada antes de compilar.

Depois do build com perfil, compare boot, estabilidade, consumo, temperatura
e frame times no mesmo jogo e cenário. Não há promessa de repetir os números
de Pixel/GKI publicados pelo Google em um Snapdragon/kernel diferente.

## Referências

* https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html
* https://docs.kernel.org/dev-tools/autofdo.html
* https://android.googlesource.com/platform/system/extras/+/master/simpleperf/doc/collect_etm_data_for_autofdo.md
* https://android.googlesource.com/kernel/common/+/b15d6439553b1a5a266ca8e0f813481f55d991dd/scripts/Makefile.autofdo
