# FranBakaSU UClamp Task Profiles — Dubai

Perfil experimental para Motorola Edge 30 (dubai), LOS 21 / Android 14,
Linux 5.4.286, com BakaSU, SUSFS, NoMount e o backport do fas-rs mantidos.

## O que mudou no kernel

A base 00cf9162 já tinha CONFIG_UCLAMP_TASK=y, CONFIG_UCLAMP_TASK_GROUP=y,
latency_sensitive e suporte a uclamp no WALT e schedutil. Eles foram preservados.
Não existe uma nova opção fictícia de configuração chamada uclamp_taskprofile.

O governador agora calcula os boosts de WALT e I/O antes de aplicar os limites
uclamp finais. Em políticas compartilhadas, cada CPU é ajustada antes de escolher
a maior demanda normalizada do grupo. O WALT usa a carga original para decidir
se precisa de hispeed, evitando confundir um piso de uclamp com carga medida.

Também foram adicionados os campos uclamp.min/max e effective uclamp.min/max em
/proc/PID/sched, seguindo o diagnóstico do Linux 5.10. Isso permite verificar o
perfil aplicado de verdade. Leituras/escritas concorrentes da indicação de baixa
latência usam READ_ONCE/WRITE_ONCE, sem alterar os layouts dos tipos do kernel.

## O que faz o módulo

O Android usa task_profiles para colocar processos no grupo de CPU top-app.
O módulo acompanha essa associação e, enquanto o Starling está nesse grupo:

- solicita um piso de utilização de 25%, preservando pisos anteriores maiores;
- ativa cpu.uclamp.latency_sensitive=1 para favorecer decisões de baixa latência;
- mantém cpu.uclamp.max, limites de frequência, afinidade, prioridade e controles
  térmicos sob o controle da ROM e do fas-rs.

25% é um sinal de utilização para o escalonador, não uma trava de clock, uma
reserva de 25% do processador ou um valor medido como ideal para todos os jogos.
O perfil vale para os membros do grupo top-app durante esse período. Não cria um
cgroup privado do jogo e não sobrescreve task_profiles.json nem cgroups.json da ROM.

Ao sair do grupo de primeiro plano, o serviço restaura os valores anteriores que
ainda correspondem aos seus próprios ajustes. Se outro controlador mudar esses
valores, ele preserva a mudança externa e suspende o perfil até o jogo sair do
grupo, evitando uma disputa contínua de escritas. Verifique profile.log nesse caso.

Os processos são descobertos a cada cinco segundos; a associação ao grupo é
conferida a cada segundo. O starttime é conferido para evitar confusão de PID
reutilizado. O módulo não mede FPS e não tenta substituir o controlador fas-rs.

## Instalação e uso

1. Instale o novo AnyKernel3 experimental e confirme o boot.
2. Mantenha o módulo fas-rs já instalado. Não é preciso instalar outra cópia dele.
3. Instale FranBakaSU-UClamp-TaskProfiles-Dubai.zip pelo BakaSU e reinicie.
4. Abra o Starling e rode o mesmo jogo/cena usados na comparação anterior.

O módulo também pode usar as interfaces já existentes no kernel anterior para
um teste A/B do perfil; as correções do governador estão no novo kernel.

Confira o log com root:

```sh
cat /data/adb/modules/fran_uclamp_profiles/profile.log
sh /data/adb/modules/fran_uclamp_profiles/profile.sh status
```

Uma linha `active io.github.juanluci.starling.preview ... min=25.00%` indica
aplicação com leitura de confirmação. Ao voltar ao Termux fora de tela dividida,
o Starling pode sair de top-app e o perfil ser liberado; isso é esperado.

Para coletar durante o jogo, execute no Termux como root e volte ao jogo por
30 segundos:

```sh
sh /data/adb/modules/fran_uclamp_profiles/collect.sh
```

Depois compartilhe `/data/local/tmp/fran-uclamp-sample.txt`. Os campos `effective
uclamp.min` mostram o valor efetivo de cada tarefa na escala 0..1024, sujeito às
restrições herdadas dos grupos e do sistema. 25% corresponde a aproximadamente 256.

Para outro jogo, adicione o nome exato do pacote em `packages.list`. O único
pacote pré-configurado é o Starling, que foi identificado nos seus logs.
`settings.conf` aceita MIN_PERCENT inteiro de 0 a 100. Reinicie após alterá-lo.
25 é um ponto de partida experimental; compare fluidez e temperatura antes de
subir esse piso. O perfil não resolve limites da GPU, compilação de shaders ou
limitações do próprio emulador.

Para parar e restaurar agora:

```sh
sh /data/adb/modules/fran_uclamp_profiles/profile.sh stop
```

Para manter desligado, desative o módulo no BakaSU e reinicie. Remover o módulo
também solicita a restauração. Em caso de falha de restauração, os registros em
/dev/.fran-uclamp-profile são retidos para recuperação; o estado de /dev e os
ajustes em memória são reinicializados no próximo boot.

## Verificação e limites

Os testes de host compilam funções reais do governador e reproduzem duas
violações dos clamps no código anterior. Também verificam o piso, limites depois
dos boosts, políticas compartilhadas e CPUs com amostras antigas.

O teste ARM64/QEMU usa o Image compilado e verifica sched_setattr/getattr, limites
inválidos, cgroup de CPU, atualização de tarefa executável e a indicação de baixa
latência, além do teste de 400 eventos eBPF do fas-rs. QEMU não reproduz o hardware
Qualcomm; os dois initcalls de firmware já usados no teste anterior são excluídos
somente na linha de comando do teste. O arquivo Image distribuído não é alterado.

Os testes do serviço usam arquivos isolados para conferir ativação apenas no
primeiro plano, restauração, piso anterior maior, máximo preservado, interferência
externa, desativação e recuperação após encerramento abrupto. Isso não substitui
medir FPS/tempo dos quadros, temperatura, consumo e boot desta versão no aparelho.

O bootstrap de instalação vem do ZIP oficial fas-rs v4.9.1 (SHA-256 fixado pelo
empacotador), sob GPL-3.0-or-later. Os scripts deste perfil são GPL-2.0-only.
