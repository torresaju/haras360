import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

/// Grava as capturas de tela do teste de integração em capturas-app/.
Future<void> main() => integrationDriver(onScreenshot: (String nome, List<int> bytes, [Map<String, Object?>? args]) async {
      final f = File('capturas-app/$nome.png');
      await f.parent.create(recursive: true);
      await f.writeAsBytes(bytes);
      return true;
    });
