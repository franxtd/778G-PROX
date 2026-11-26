# FranBakaSU + SUSFS no Dubai (LineageOS 21)

Base: Linux 5.4.286 do Motorola Edge 30 (`dubai`), LineageOS 21 / Android 14.

## Revisões

| Componente | Revisão |
| --- | --- |
| Kernel de referência anterior ao SUSFS | `0db0715450389d0e2bc5688972f696027860afcf` |
| BakaSU (mantido do build 30) | `57b2db6076f439cfd489f14576444e8f0f2f0a25` |
| Backport SUSFS 2.4.0, JackA1ltman/NonGKI_Kernel_Build_2nd | `ec069a4e34f992d602a6b40d2e211df2516e2865` |
| AOSP Clang r614150 / 23.0.1 | `16fae8ef5b856b1d3e02a55274e4327c5842bb34` |
| AnyKernel3 | `41f04bdb4ee30a44e429c2c1131d5e8bb32b15f1` |

O backport utilizado é `Patches/Patch/susfs_patch_to_5.4.patch` do repositório
https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd . Seus autores e o SUSFS
original de simonpunk (https://gitlab.com/simonpunk/susfs4ksu) mantêm seus créditos.
Os arquivos são distribuídos sob a licença do kernel, conforme `COPYING`.

## Integração específica desta árvore

- VFS, namespaces, procfs, metadados, mapas de memória e operações de montagem
  usam o backport próprio para 5.4, sem transportar estruturas de kernel 5.10.
- Os hooks de exec, access, stat, read, input, setresuid e reboot foram adaptados
  para a interface SUSFS do BakaSU fixado acima.
- Em exec, a referência de `struct filename` permanece válida até o callback
  posterior. Se o runner preinit falhar, a execução de init é tentada novamente
  com uma nova referência; não se reutiliza a referência consumida pela primeira
  tentativa de `__do_execve_file()`.
- O retorno da supercall do BakaSU é respeitado em reboot, antes do fluxo normal.
- O identificador da variante SUSFS é `NON-GKI` nesta versão de kernel.
- O include desnecessário de `fs/mount.h` foi removido de `fs/statfs.c`.
  Ele mudava a expansão de tipos vista por genksyms e alterava os CRCs de
  `vfs_get_fsid` e `vfs_statfs`. A remoção preserva os CRCs originais sem
  alterar ou desativar o mecanismo de versionamento de símbolos.
- `CONFIG_KSU_SUSFS=y` seleciona os hooks SUSFS. O modo manual anterior é
  desativado. CFI, ThinLTO, versão base e configurações do dispositivo seguem o
  build 30 anterior. As opções novas são as de SUSFS.

## Compilação

O workflow `.github/workflows/build-dubai.yml` baixa o BakaSU fixado e o Clang,
usa `vendor/franbakasu_susfs_defconfig`, compila Image, módulos e device trees,
e empacota um AnyKernel3 para o Dubai. A conexão `drivers/kernelsu` já está
versionada; não se deve inserir novamente Kconfig, Makefile ou hooks.

Para reproduzir localmente em Linux, instale as dependências listadas no workflow,
coloque os binários do Clang r614150 no PATH, clone o BakaSU em `KernelSU/` e faça
checkout da revisão indicada na tabela. Então execute:

```sh
export ARCH=arm64 SUBARCH=arm64
make O=out LLVM=1 LLVM_IAS=1 vendor/franbakasu_susfs_defconfig
make O=out LLVM=1 LLVM_IAS=1 headers_install
make O=out LLVM=1 LLVM_IAS=1 security/selinux/ init/version.o
make O=out LLVM=1 LLVM_IAS=1 drivers/kernelsu/
make -j8 O=out LLVM=1 LLVM_IAS=1 Image
make -j8 O=out LLVM=1 LLVM_IAS=1 dtbs modules
```

O workflow explicita também HOSTCC, HOSTCXX, ferramentas LLVM, DTC e LZ4 para
evitar a seleção de ferramentas incompatíveis pelo ambiente.

## Validação e instalação

A compilação e a inspeção estática não validam o boot no aparelho. O ZIP
experimental contém o kernel e o instalador AnyKernel3; ele preserva o ramdisk
existente e não instala módulos, DTBO ou vendor_boot. Use somente no dispositivo
e na ROM acima. Mantenha o backup pré-SUSFS para recuperação.

Após testar o boot no aparelho, confira a versão do kernel, o root pelo BakaSU,
o reconhecimento da versão SUSFS no gerenciador, os logs do kernel e as funções
do dispositivo. As regras SUSFS de espaço de usuário devem ser compatíveis com
SUSFS 2.4.0. Esse teste de execução requer o aparelho.
