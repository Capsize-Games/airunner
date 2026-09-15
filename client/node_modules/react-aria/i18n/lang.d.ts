import type {LocalizedString} from '@internationalized/string';

type PackageLocalizedStrings = {
  [packageName: string]: Record<string, LocalizedString>
}

export default PackageLocalizedStrings;
