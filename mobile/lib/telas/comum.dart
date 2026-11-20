import 'package:flutter/material.dart';

import '../regras_app.dart';
import '../tema.dart';

class Secao extends StatelessWidget {
  final String titulo;
  final String? contador;
  final List<Widget> filhos;
  final String vazio;
  const Secao(this.titulo, this.filhos, {super.key, this.contador, this.vazio = ''});

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Expanded(child: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
              if (contador != null) Text(contador!, style: const TextStyle(color: Cores.apagado)),
            ]),
            const SizedBox(height: 6),
            if (filhos.isEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text(vazio, style: const TextStyle(color: Cores.apagado))),
            ...filhos,
          ]),
        ),
      );
}

class LinhaTarefa extends StatelessWidget {
  final Map t;
  final VoidCallback onRegistrar;
  final bool mostrarAnimal;
  const LinhaTarefa(this.t, {super.key, required this.onRegistrar, this.mostrarAnimal = true});

  @override
  Widget build(BuildContext context) {
    final dose = doseTxt(t['dose']);
    return InkWell(
      onTap: onRegistrar,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(mostrarAnimal ? '${t['titulo']} · ${t['animal']}' : '${t['titulo']}', style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text([t['etapa'], if (dose.isNotEmpty) dose, br(t['due'] as String?)].whereType<String>().join(' · '), style: const TextStyle(color: Cores.apagado, fontSize: 13)),
              const SizedBox(height: 4),
              Etiqueta.status(t['status'] as String? ?? 'futuro', relativo(t['due'] as String?)),
            ]),
          ),
          const SizedBox(width: 8),
          OutlinedButton(onPressed: onRegistrar, child: const Text('Registrar')),
        ]),
      ),
    );
  }
}
