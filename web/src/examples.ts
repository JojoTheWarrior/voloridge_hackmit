import ideas from '../../shared/starter-ideas.json'
import datasets from '../../shared/starter-datasets.json'

export const STARTER_IDEAS = ideas.suggestions
export const EXAMPLE_PROMPTS = STARTER_IDEAS.slice(0, 3).map((idea) => idea.text)
export const STARTER_DATASETS = datasets
