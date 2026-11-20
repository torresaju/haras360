// Versão do app, passada no build: --dart-define=APP_VERSAO=1.1.0 --dart-define=APP_CODIGO=10100
const appVersao = String.fromEnvironment('APP_VERSAO', defaultValue: '0.0.0');
const appCodigo = int.fromEnvironment('APP_CODIGO', defaultValue: 0);

const tarefaSincronizacao = 'haras360-sincronizar';
const intervaloSincronizacao = Duration(hours: 1);
const maxFotos = 4;
