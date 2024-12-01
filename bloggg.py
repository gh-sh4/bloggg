import argparse
import yaml
import mistletoe
import os
import shutil
from pathlib import Path
import re

# File types that are copied directly to the output directory
DIRECT_COPY_EXTENSIONS = set(['.html', '.css', '.js', '.png', '.jpg', '.svg'])

# Super simple markdown frontmatter parser. Returns frontmatter and markdown content 
# without frontmatter
def parse_frontmatter(markdown: str):
    # Find all content between `---` and `---`, parse as yaml
    start = markdown.find('---')
    end = markdown.find('---', start + 3)
    if start != -1 and end != -1:
        return yaml.safe_load(markdown[start + 3:end]), markdown[end + 3:]
    return None, markdown

# Recurse through a directory and yield all files with the given extensions
def walk_dir(dir: Path, extensions: set[str]):
    for root, _dirs, files in os.walk(dir):
        for file in files:
            if Path(file).suffix in extensions:
                yield Path(root) / file

# Patch all referenced files (href="...") to be relative to the root of the output directory
# relative_path is the path of the output file relative to the output directory
def patch_referenced_files(final_html: str, template_file: Path, markdown_file: Path):
    for match in re.finditer(r'(href|src)="([^"]+)"', final_html):
        attr, file = match.groups()
        if not file.startswith('http') and not file.startswith('#'):

            # Construct a path down from the markdown file to the `/_templates` directory
            markdown_to_root = '../' * len(markdown_file.parts[:-2]) + '_templates'
            asset_path = f'{markdown_to_root}/{file}'
            print(f' - asset {asset_path}')

            # Replace the match with asset_path
            final_html = final_html[:match.start(2)] + asset_path + final_html[match.end(2):]
    
    return final_html

# Generates a little navigation breadcrumb list of links for a page
def gen_breadcrumbs_html(file_dir: Path, input_root: Path):
    # Generate breadcrumbs
    breadcrumbs = []

    file_dir = file_dir.with_suffix('')
    
    # Dont' generate "... / index"
    if file_dir.name == 'index':
        file_dir = file_dir.parent

    # Generate all the breadcrumbs up to the root
    while file_dir != input_root:
        breadcrumbs.append(file_dir)
        file_dir = file_dir.parent
    breadcrumbs.append(input_root)

    # If there's only one breadcrumb (probably root page) don't generate anything
    if len(breadcrumbs) == 1:
        return ''

    # Generate html
    html = '<nav class="breadcrumbs">'
    for i, crumb in enumerate(breadcrumbs[::-1]):
        if i != 0:
            html += ' / '
        name = 'root' if i == 0 else crumb.name
        html += f'<a href="{"/".join([".."] * (len(breadcrumbs) - 1 - i))}">{name}</a>'
    html += '</nav>'
    return html

# Process a single markdown file
def process_markdown(file: Path, input_root: Path, output_root: Path):
    file_dir = file.parent if file.is_file() else file
    with open(file, 'r') as f:
        output_file = output_root / file.relative_to(input_root).with_suffix('.html')
        print(f'processing {file} -> {output_file}')

        content = f.read()

        # Parse frontmatter, find template, else use default template
        frontmatter, content = parse_frontmatter(content)
        template_name = frontmatter.get('template', 'default').strip()
        template_file = input_root / '_templates' / f'{template_name}.html'
        assert template_file.exists(), f'template {template_file} does not exist'
        with open(template_file, 'r') as f:
            template = f.read()

        # Patch all referenced files (href="...") to be relative to the root of the output directory
        # This happens on the base template to avoid messing with links etc. generated from the markdown
        template = patch_referenced_files(template, template_file, file)

        # Render markdown content, replace template variables
        content_html = mistletoe.markdown(content)
        template = template.replace('$$DOC_TITLE$$', frontmatter.get('title', ''))
        if 'date' in frontmatter:
            template = template.replace('$$DOC_DATE$$', f"Written {str(frontmatter.get('date'))}")
        else:
            template = template.replace('$$DOC_DATE$$', '')
        template = template.replace('$$DOC_CONTENT$$', content_html)
        template = template.replace('$$BREADCRUMBS$$', gen_breadcrumbs_html(file, input_root))
        
        # Write to output file
        output_file = output_root / file.relative_to(input_root).with_suffix('.html')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(template)

def process_all(input_root: Path, output_root: Path):
    # Copy all non-template html files
    for file in walk_dir(input_root, DIRECT_COPY_EXTENSIONS):
        # Don't process files with `_templates` in any of the directories
        if '_templates' in file.parts:
            continue

        output_file = output_root / file.relative_to(input_root)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        print(f'processing {file} -> {output_file}')
        shutil.copy(file, output_file)

    # Create output template directory with every file that isn't html (images, css, etc.)
    out_template_dir = output_root / '_templates'
    out_template_dir.mkdir(parents=True, exist_ok=True)
    for file in walk_dir(input_root / '_templates', DIRECT_COPY_EXTENSIONS - set(['.html'])):
        output_file = out_template_dir / file.relative_to(input_root / '_templates')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        print(f'processing {file} -> {output_file}')
        shutil.copy(file, output_file)
    
    # Process all markdown files
    for file in walk_dir(input_root, ['.md']):
        process_markdown(file, input_root, output_root)

def main():
    parser = argparse.ArgumentParser(description='mds - markdown site generator')
    parser.add_argument('-w', '--watch', help='watch mode', action='store_true')
    parser.add_argument('-i', '--input', help='input directory', required=True)
    parser.add_argument('-o', '--output', help='output directory', required=True)
    args = parser.parse_args()

    # Assert input directory exists
    input_root  = Path(args.input)
    output_root = Path(args.output)
    assert input_root.exists(), f'{input_root} does not exist'

    process_all(input_root, output_root)
    
    # If watch mode is enabled, watch for changes and reprocess markdown files. Any other
    # file changes will be stupid and just re-process everything rather than be clever
    if args.watch:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                # Make everything relative paths
                event_src_relative = os.path.relpath(event.src_path, os.getcwd())
                if event_src_relative.endswith('.md'):
                    process_markdown(Path(event_src_relative), input_root, output_root)
                else:
                    process_all(input_root, output_root)

        observer = Observer()
        observer.schedule(Handler(), str(input_root), recursive=True)
        observer.start()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

if __name__ == '__main__':
    main()
