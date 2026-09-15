import React from 'react';
import type {LocalizedStringDictionary} from '@internationalized/string';

interface LocalizedStringProviderProps {
  locale: string,
  dictionary?: LocalizedStringDictionary,
  nonce?: string
}

export declare function LocalizedStringProvider(props: LocalizedStringProviderProps): React.JSX.Element;
export declare function getLocalizationScript(locale: string, dictionary?: LocalizedStringDictionary): string;
export declare const dictionary: LocalizedStringDictionary;
export declare function createLocalizedStringDictionary(packages: string[]): LocalizedStringDictionary;
