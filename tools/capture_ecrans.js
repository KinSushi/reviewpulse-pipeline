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
