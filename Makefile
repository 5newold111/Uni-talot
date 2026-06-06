.PHONY: install test daily release clean

install:
	pip install -r requirements.txt pytest

test:
	MUSIC_PIPELINE_MOCK=1 pytest -q

# モックモードで1日分を生成（API キー不要）
daily:
	MUSIC_PIPELINE_MOCK=1 python scripts/run_daily.py

# モックモードでアルバムをパッケージ化
release:
	MUSIC_PIPELINE_MOCK=1 python scripts/run_release.py --force

clean:
	rm -rf output state/state.json .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
