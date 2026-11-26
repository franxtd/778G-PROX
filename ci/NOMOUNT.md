# NoMount no FranBakaSU / Dubai

Integração nativa do NoMount v2.3.1 no Linux 5.4.286 do Motorola Edge 30
(`dubai`), com LineageOS 21 / Android 14, BakaSU e SUSFS 2.4.0.

## Fontes

| Componente | Revisão |
| --- | --- |
| Base com SUSFS | `f1faa96af37873ea9f7c532efdb059ac65322e7e` |
| NoMount v2.3.1 | `dcd77d03e9912f397a586d7da81694d1628f170e` |
| BakaSU | `57b2db6076f439cfd489f14576444e8f0f2f0a25` |
| AOSP Clang r614150 / 23.0.1 | `16fae8ef5b856b1d3e02a55274e4327c5842bb34` |

Projeto original: https://github.com/maxsteeel/nomount

`fs/nomount/` contém os arquivos originais de `kernel/src/` dessa revisão e sua
licença GPL-2.0. O arquivo `UPSTREAM` registra a origem. A integração adiciona a
entrada em `fs/Kconfig`, o alvo em `fs/Makefile` e `CONFIG_NOMOUNT=y` ao defconfig
do Dubai. `CONFIG_KEYS=y` já estava ativo. O código C e o header do NoMount não
precisaram de backport adicional para essa árvore.

O NoMount é compilado dentro da Image. Seu controle usa o keyring `nomount`,
registrado durante a inicialização do kernel. O código original exige
`CAP_SYS_ADMIN` para os comandos. A integração não inclui regras de redireção
predefinidas.

Os hooks SUSFS e o driver BakaSU da base são mantidos. A compilação continua com
CFI e ThinLTO ativos. As informações de compilação NoMount podem ser conferidas
em `out/fs/nomount/.nomount.o.cmd` e em `out/.config`.

## Compilação

O workflow `.github/workflows/build-dubai.yml` usa o defconfig
`vendor/franbakasu_susfs_defconfig`, que nesta branch também habilita NoMount.
Os fontes NoMount já estão versionados; não é necessário executar `setup.sh`
nem baixar outra revisão durante a compilação.

Use o mesmo Clang e as mesmas dependências descritas em `ci/SUSFS.md` e no
workflow. Com BakaSU fixado em `KernelSU/`, os alvos são:

```sh
export ARCH=arm64 SUBARCH=arm64
make O=out LLVM=1 LLVM_IAS=1 vendor/franbakasu_susfs_defconfig
make O=out LLVM=1 LLVM_IAS=1 headers_install
make O=out LLVM=1 LLVM_IAS=1 security/selinux/ init/version.o
make O=out LLVM=1 LLVM_IAS=1 fs/nomount/ drivers/kernelsu/
make -j8 O=out LLVM=1 LLVM_IAS=1 Image dtbs modules
```

## Uso no aparelho

O AnyKernel3 experimental instala o kernel no boot ativo, seguindo o empacotamento
anterior do Dubai. A instalação e o boot precisam ser testados no aparelho.

Para gerenciar módulos por NoMount, instale no BakaSU o metamódulo oficial
**NoMount v2.3.1**, publicado em:
https://github.com/maxsteeel/nomount/releases/tag/v2.3.1

O instalador oficial verifica a presença do suporte nativo antes de tentar
carregar um LKM. Após um boot e uma instalação bem-sucedidos, confira a versão:

```sh
su -c '/data/adb/modules/nomount/bin/nm version'
```

O kernel NoMount dessa versão anuncia a interface `23`, conforme o upstream.
O metamódulo fornece o gerenciamento de regras, os scripts de inicialização e a
WebUI. A compilação do kernel não substitui a instalação desse componente.

O identificador de release do kernel acompanha a revisão da base Git. Na
validação de módulos, o release é comparado com o kernel recém-compilado, e os
demais campos de vermagic e os CRCs exportados são comparados com a base SUSFS.
Essas verificações estáticas não substituem os testes de boot, root, NoMount,
Wi-Fi, áudio e demais funções no aparelho.
