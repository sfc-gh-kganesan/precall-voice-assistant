import { item } from '@1password/op-js';

export type SnowflakePat1p = {
	value: string;
	vault: string;
	item: string;
};

export function getSnowflakePat(
	itemTag = 'p67',
	vault = 'Employee',
): SnowflakePat1p {
	const items = item.list({ vault, tags: [itemTag] });
	const selectedItem = items[0];

	if (!selectedItem) {
		throw new Error(`No item found with tag ${itemTag} in ${vault} vault`);
	}

	const itemId = selectedItem.id;
	const itemDetails = item.get(itemId);

	if (
		!itemDetails ||
		typeof itemDetails !== 'object' ||
		!('fields' in itemDetails) ||
		itemDetails.fields === undefined
	) {
		throw new Error('Invalid item structure returned');
	}

	const patField = itemDetails.fields.find((f) => f.label === 'password');

	if (!patField) {
		throw new Error(
			`Password field not found in ${vault}.${selectedItem.title}`,
		);
	}

	return {
		value: patField.value,
		vault: selectedItem.vault.name,
		item: selectedItem.title,
	};
}
