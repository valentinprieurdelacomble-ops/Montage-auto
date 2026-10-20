// Fabrique les cartes animées (inserts) avec Remotion.
// Usage : node rendre.mjs travail.json
// travail.json = {"inserts": [{"props": {...}, "sortie": "chemin.mov"}], "processus": null}
// Chaque carte est une vidéo transparente (ProRes 4444) posée ensuite par FFmpeg sur la vidéo.
import {bundle} from '@remotion/bundler';
import {ensureBrowser, openBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import {createHash} from 'node:crypto';
import {cpSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ICI = path.dirname(fileURLToPath(import.meta.url));
const travail = JSON.parse(readFileSync(process.argv[2], 'utf-8'));

// Polices : copiées depuis assets/fonts pour que Remotion les trouve
mkdirSync(path.join(ICI, 'public', 'fonts'), {recursive: true});
for (const f of readdirSync(path.join(ICI, '..', 'assets', 'fonts'))) {
	if (f.endsWith('.ttf')) cpSync(path.join(ICI, '..', 'assets', 'fonts', f), path.join(ICI, 'public', 'fonts', f));
}

// Le "paquet" Remotion n'est refait que si le code des cartes a changé (gain de temps).
const empreinte = (() => {
	const h = createHash('sha1');
	const parcourir = (d) => {
		for (const f of readdirSync(d).sort()) {
			const p = path.join(d, f);
			if (statSync(p).isDirectory()) parcourir(p);
			else h.update(f).update(readFileSync(p));
		}
	};
	parcourir(path.join(ICI, 'src'));
	return h.digest('hex').slice(0, 12);
})();
const dossierPaquet = path.join(ICI, '.paquet', empreinte);
let serveUrl = dossierPaquet;
if (!existsSync(path.join(dossierPaquet, 'index.html'))) {
	console.log('  • Préparation des modèles d\'animation (une seule fois)');
	serveUrl = await bundle({entryPoint: path.join(ICI, 'src', 'index.ts'), outDir: dossierPaquet, publicDir: path.join(ICI, 'public')});
}

const navigateur = process.env.MONTAGE_NAVIGATEUR || null;
if (!navigateur) {
	// 1er lancement : télécharge le navigateur invisible utilisé par Remotion
	await ensureBrowser();
}
const browser = await openBrowser('chrome', {browserExecutable: navigateur});

try {
	for (const [i, ins] of travail.inserts.entries()) {
		const t0 = Date.now();
		const composition = await selectComposition({serveUrl, id: 'Insert', inputProps: ins.props, puppeteerInstance: browser, browserExecutable: navigateur});
		const temporaire = ins.sortie + '.en_cours.mov';
		await renderMedia({
			composition,
			serveUrl,
			inputProps: ins.props,
			codec: 'prores',
			proResProfile: '4444',
			imageFormat: 'png',
			pixelFormat: 'yuva444p10le',
			outputLocation: temporaire,
			puppeteerInstance: browser,
			browserExecutable: navigateur,
			concurrency: travail.processus ?? null,
			overwrite: true,
		});
		const {renameSync} = await import('node:fs');
		renameSync(temporaire, ins.sortie);
		console.log(`  • Carte ${i + 1}/${travail.inserts.length} (${ins.props.type}) prête en ${((Date.now() - t0) / 1000).toFixed(0)} s`);
	}
} finally {
	await browser.close({silent: true});
}
writeFileSync(process.argv[2] + '.ok', 'ok');
