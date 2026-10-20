// Télécharge à l'avance le navigateur invisible dont Remotion a besoin (une seule fois).
import {ensureBrowser} from '@remotion/renderer';

await ensureBrowser();
console.log('Navigateur de rendu prêt.');
