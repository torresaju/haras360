// Versão do app, passada no build: --dart-define=APP_VERSAO=1.1.0 --dart-define=APP_CODIGO=10100
const appVersao = String.fromEnvironment('APP_VERSAO', defaultValue: '0.0.0');
const appCodigo = int.fromEnvironment('APP_CODIGO', defaultValue: 0);

const tarefaSincronizacao = 'haras360-sincronizar';
const intervaloSincronizacao = Duration(hours: 1);
const intervaloGestor = Duration(minutes: 15); // v1.5.0: avisos do gestor (mínimo do Android)
const tarefaAvisos = 'haras360-avisos';
const maxFotos = 4;
