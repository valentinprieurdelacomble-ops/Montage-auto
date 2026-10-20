import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {apparition, progression} from '../anim';
import {Etiquette, tailleTexte} from '../Carte';
import {alpha, Couleurs} from '../theme';

// 2. Avant / après : la phrase faible est barrée, la phrase forte la remplace.
export const AvantApres: React.FC<{avant: string; apres: string; couleurs: Couleurs}> = ({avant, apres, couleurs}) => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();
	const total = durationInFrames / fps;
	// rythme adapté à la durée de l'insert
	const tBarre = Math.round(Math.min(1.1, total * 0.27) * fps);
	const tApres = tBarre + Math.round(0.45 * fps);
	const barre = progression(frame, tBarre, Math.round(0.35 * fps));
	const pApres = progression(frame, tApres, Math.round(0.4 * fps));
	const tailleAvant = tailleTexte(avant, 54, 38, 80);
	const tailleApres = tailleTexte(apres, 64, 42, 80);
	return (
		<div style={{display: 'flex', flexDirection: 'column', gap: 34}}>
			<div style={apparition(frame, 6, 10)}>
				<Etiquette texte="Avant" couleur={alpha(couleurs.blanc, 0.45)} style={{marginBottom: 12}} />
				<div style={{position: 'relative', display: 'inline-block'}}>
					<div
						style={{
							fontWeight: 600,
							fontSize: tailleAvant,
							lineHeight: 1.2,
							color: alpha(couleurs.blanc, 0.6 - 0.25 * barre),
						}}
					>
						{avant}
					</div>
					{/* trait qui barre la phrase */}
					<div
						style={{
							position: 'absolute',
							left: -6,
							top: '52%',
							height: 5,
							borderRadius: 3,
							width: `calc(${barre * 100}% + 12px)`,
							background: alpha(couleurs.blanc, 0.85),
						}}
					/>
				</div>
			</div>
			<div style={{height: 1.5, background: alpha(couleurs.blanc, 0.08), width: `${100 * pApres}%`}} />
			<div style={{display: 'flex', gap: 24, opacity: pApres, translate: `0px ${(1 - pApres) * 22}px`}}>
				<div style={{width: 7, borderRadius: 4, background: couleurs.bleu, scale: `1 ${pApres}`, transformOrigin: 'top'}} />
				<div>
					<Etiquette texte="Après" couleur={couleurs.bleu} style={{marginBottom: 12}} />
					<div style={{fontWeight: 800, fontSize: tailleApres, lineHeight: 1.15, letterSpacing: -0.5}}>{apres}</div>
				</div>
			</div>
		</div>
	);
};
