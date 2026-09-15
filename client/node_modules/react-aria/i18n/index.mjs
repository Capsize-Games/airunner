import {PackageLocalizationProvider, getPackageLocalizationScript} from 'react-aria/private/i18n/server';
import {LocalizedStringDictionary} from '@internationalized/string';
import {createElement} from 'react';
import zh_TW from './zh-TW.mjs';
import zh_CN from './zh-CN.mjs';
import uk_UA from './uk-UA.mjs';
import tr_TR from './tr-TR.mjs';
import sv_SE from './sv-SE.mjs';
import sr_SP from './sr-SP.mjs';
import sl_SI from './sl-SI.mjs';
import sk_SK from './sk-SK.mjs';
import ru_RU from './ru-RU.mjs';
import ro_RO from './ro-RO.mjs';
import pt_PT from './pt-PT.mjs';
import pt_BR from './pt-BR.mjs';
import pl_PL from './pl-PL.mjs';
import nl_NL from './nl-NL.mjs';
import nb_NO from './nb-NO.mjs';
import lv_LV from './lv-LV.mjs';
import lt_LT from './lt-LT.mjs';
import ko_KR from './ko-KR.mjs';
import ja_JP from './ja-JP.mjs';
import it_IT from './it-IT.mjs';
import hu_HU from './hu-HU.mjs';
import hr_HR from './hr-HR.mjs';
import he_IL from './he-IL.mjs';
import fr_FR from './fr-FR.mjs';
import fi_FI from './fi-FI.mjs';
import et_EE from './et-EE.mjs';
import es_ES from './es-ES.mjs';
import en_US from './en-US.mjs';
import el_GR from './el-GR.mjs';
import de_DE from './de-DE.mjs';
import da_DK from './da-DK.mjs';
import cs_CZ from './cs-CZ.mjs';
import bg_BG from './bg-BG.mjs';
import ar_AE from './ar-AE.mjs';

let dictionary = new LocalizedStringDictionary({
  "zh-TW": zh_TW,
  "zh-CN": zh_CN,
  "uk-UA": uk_UA,
  "tr-TR": tr_TR,
  "sv-SE": sv_SE,
  "sr-SP": sr_SP,
  "sl-SI": sl_SI,
  "sk-SK": sk_SK,
  "ru-RU": ru_RU,
  "ro-RO": ro_RO,
  "pt-PT": pt_PT,
  "pt-BR": pt_BR,
  "pl-PL": pl_PL,
  "nl-NL": nl_NL,
  "nb-NO": nb_NO,
  "lv-LV": lv_LV,
  "lt-LT": lt_LT,
  "ko-KR": ko_KR,
  "ja-JP": ja_JP,
  "it-IT": it_IT,
  "hu-HU": hu_HU,
  "hr-HR": hr_HR,
  "he-IL": he_IL,
  "fr-FR": fr_FR,
  "fi-FI": fi_FI,
  "et-EE": et_EE,
  "es-ES": es_ES,
  "en-US": en_US,
  "el-GR": el_GR,
  "de-DE": de_DE,
  "da-DK": da_DK,
  "cs-CZ": cs_CZ,
  "bg-BG": bg_BG,
  "ar-AE": ar_AE,
});

function LocalizedStringProvider({locale, dictionary: dict = dictionary, nonce}) {
  let strings = dict.getStringsForLocale(locale);
  return createElement(PackageLocalizationProvider, {locale, strings, nonce});
}

function getLocalizationScript(locale, dict = dictionary) {
  let strings = dict.getStringsForLocale(locale);
  return getPackageLocalizationScript(locale, strings);
}

let deps = {};

function createLocalizedStringDictionary(packages) {
  let strings = {};
  let seen = new Set();
  let addPkg = (pkg) => {
    if (seen.has(pkg)) {
      return;
    }
    seen.add(pkg);

    for (let lang in dictionary.strings) {
      strings[lang] ??= {};
      strings[lang][pkg] = dictionary.strings[lang][pkg];
    }

    for (let dep of deps[pkg] || []) {
      addPkg(dep);
    }
  };

  
  for (let pkg of packages) {
    addPkg(pkg);
  }

  return new LocalizedStringDictionary(strings);
}
export {LocalizedStringProvider, getLocalizationScript, dictionary, createLocalizedStringDictionary};
