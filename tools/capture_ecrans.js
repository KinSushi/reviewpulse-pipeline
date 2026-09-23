// Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
// Pourquoi ce script existe -- un navigateur sans interface lance avec --screenshot photographie Streamlit avant que le websocket n'ait livre les donnees (trois captures vides le 20/09/2026)
// ici on attend le rendu reel : reseau calme, puis un delai fixe, puis la photo.
// Ce script capture deux pages distinctes pour verification visuelle.
// Il utilise puppeteer en mode headless nouveau.
// demarrage de Chromium superieur a trente secondes sur un disque externe lent, constate le 21/09/2026
// barre laterale de Streamlit a moitie hors champ en rendu sans interface, constate le 21/09/2026

const puppeteer = require('puppeteer');

const CIBLES = [
  {
    nom: 'tableau_de_bord',
    url: 'http://host.docker.internal:8501',
    largeur: 1440,
    hauteur: 1200,
    attente: 25000,
    pleinePage: false,
    cadre: { x: 470, y: 90, width: 800, height: 1090 },
  },
  {
    // Etape du discours : « je tape un avis a la main » -- la zone de saisie du tableau de bord.
    nom: 'tableau_de_bord_saisie',
    url: 'http://host.docker.internal:8501',
    largeur: 1440,
    hauteur: 2400,
    attente: 25000,
    pleinePage: false,
    avant: 'saisie',
    cadre: { x: 470, y: 90, width: 800, height: 2200 },
  },
  {
    nom: 'api_predict_essai',
    url: 'http://host.docker.internal:8000/docs',
    largeur: 1440,
    hauteur: 1400,
    attente: 8000,
    pleinePage: false,
    avant: 'predict',
  },
  {
    nom: 'api_metrics',
    url: 'http://host.docker.internal:8000/metrics',
    largeur: 1100,
    hauteur: 600,
    attente: 3000,
    pleinePage: false,
  },
  {
    nom: 'mlflow_experiences',
    url: 'http://host.docker.internal:5000/#/experiments',
    largeur: 1440,
    hauteur: 1000,
    attente: 12000,
    pleinePage: false,
  },
  {
    nom: 'mlflow_modele',
    url: 'http://host.docker.internal:5000/#/models/reviewpulse-sentiment',
    largeur: 1440,
    hauteur: 1000,
    attente: 12000,
    pleinePage: false,
  },
];

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    timeout: 300000,
    protocolTimeout: 300000,
  });

  for (const c of CIBLES) {
    let page;
    try {
      page = await browser.newPage();
      await page.setViewport({ width: c.largeur, height: c.hauteur });
      await page.goto(c.url, { waitUntil: 'networkidle2', timeout: 180000 });
      await new Promise((r) => setTimeout(r, c.attente));
      // Actions optionnelles avant la photo : ce que la demonstration fait a l'ecran.
      if (c.avant === 'saisie') {
        // Pourquoi : la phrase du discours, mot pour mot, tapee dans la premiere zone de texte libre.
        const zone = await page.$('textarea');
        if (zone) {
          await zone.click({ clickCount: 3 });
          await zone.type('injouable, plein de bugs, remboursez-moi');
          // Le bouton « Envoyer pour prédiction » : on le trouve par son texte, quel que soit son rang.
          const boutons = await page.$$('button');
          for (const b of boutons) {
            const t = await b.evaluate((el) => el.innerText);
            if (t && t.includes('Envoyer')) { await b.click(); break; }
          }
          await new Promise((r) => setTimeout(r, 12000));
          await zone.evaluate((el) => el.scrollIntoView({ block: 'start' }));
          await new Promise((r) => setTimeout(r, 1500));
        }
      }
      if (c.avant === 'predict') {
        // Pourquoi : la documentation interactive, avec le point d'acces /predict deplie et son essai.
        const bouton = await page.$('#operations-default-predict_predict_post .opblock-summary');
        if (bouton) {
          await bouton.click();
          await new Promise((r) => setTimeout(r, 1500));
          const essai = await page.$('#operations-default-predict_predict_post .try-out__btn');
          if (essai) { await essai.click(); await new Promise((r) => setTimeout(r, 1000)); }
          const corps = await page.$('#operations-default-predict_predict_post textarea');
          if (corps) {
            // Pourquoi : un triple-clic ne selectionne qu'un paragraphe de l'exemple ; on vide tout.
            await corps.click();
            await page.keyboard.down('Control'); await page.keyboard.press('a'); await page.keyboard.up('Control');
            await page.keyboard.press('Backspace');
            await corps.type('{"texts": ["injouable, plein de bugs, remboursez-moi", "great game, I love it"]}');
            const exec = await page.$('#operations-default-predict_predict_post .execute');
            if (exec) { await exec.click(); await new Promise((r) => setTimeout(r, 6000)); }
          }
          await bouton.evaluate((el) => el.scrollIntoView({ block: 'start' }));
          await new Promise((r) => setTimeout(r, 1000));
        }
      }

      const options = { path: '/out/' + c.nom + '.png' };
      if (c.cadre) {
        options.clip = c.cadre;
      } else {
        options.fullPage = c.pleinePage;
      }
      await page.screenshot(options);

      console.log('capture ecrite : ' + c.nom + '.png');
    } catch (e) {
      console.log('echec ' + c.nom + ' : ' + e.message);
    } finally {
      if (page) {
        await page.close();
      }
    }
  }

  await browser.close();
})().catch((e) => {
  console.log('erreur fatale : ' + e.message);
});
