import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Carte} from './Carte';
import {AvantApres} from './inserts/AvantApres';
import {Citation} from './inserts/Citation';
import {Etapes} from './inserts/Etapes';
import {Jauge} from './inserts/Jauge';
import {Liste} from './inserts/Liste';
import {COULEURS_DEFAUT, Couleurs} from './theme';

export type InsertProps = {
	type: 'citation' | 'avant_apres' | 'etapes' | 'liste' | 'jauge';
	duree: number; // secondes
	largeur: number;
	hauteur: number;
	couleurs?: Couleurs;
	texte?: string;
	auteur?: string;
	avant?: string;
	apres?: string;
	titre?: string;
	elements?: string[];
	moments?: number[]; // secondes depuis le début de l'insert
	valeur?: number;
	unite?: string;
	libelle?: string;
	max?: number;
	barre?: boolean;
};

const Insert: React.FC<InsertProps> = (props) => {
	const couleurs = props.couleurs ?? COULEURS_DEFAUT;
	const contenu = (() => {
		switch (props.type) {
			case 'citation':
				return <Citation texte={props.texte ?? ''} auteur={props.auteur} moments={props.moments} couleurs={couleurs} />;
			case 'avant_apres':
				return <AvantApres avant={props.avant ?? ''} apres={props.apres ?? ''} couleurs={couleurs} />;
			case 'etapes':
				return <Etapes titre={props.titre} elements={props.elements ?? []} moments={props.moments} couleurs={couleurs} />;
			case 'liste':
				return <Liste titre={props.titre} elements={props.elements ?? []} moments={props.moments} couleurs={couleurs} />;
			case 'jauge':
				return (
					<Jauge
						valeur={props.valeur ?? 0}
						unite={props.unite}
						libelle={props.libelle}
						max={props.max}
						barre={props.barre}
						couleurs={couleurs}
					/>
				);
			default:
				return null;
		}
	})();
	return <Carte couleurs={couleurs}>{contenu}</Carte>;
};

const metadonnees: CalculateMetadataFunction<InsertProps> = ({props}) => ({
	durationInFrames: Math.max(1, Math.round(props.duree * 30)),
	width: props.largeur,
	height: props.hauteur,
});

const EXEMPLE: InsertProps = {
	type: 'liste',
	duree: 4.5,
	largeur: 1080,
	hauteur: 640,
	titre: '3 RÈGLES SIMPLES',
	elements: ['Ralentis ton débit', 'Regarde ton public', 'Fais une pause'],
};

export const Racine: React.FC = () => (
	<Composition
		id="Insert"
		component={Insert}
		fps={30}
		width={1080}
		height={640}
		durationInFrames={135}
		defaultProps={EXEMPLE}
		calculateMetadata={metadonnees}
	/>
);
