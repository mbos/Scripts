#!/bin/bash
# ConvertDocument.sh
# Script to convert between Microsoft Word and Markdown formats using pandoc
# Version: 0.2
# Copyright 2025 Mike Bos
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Function to handle errors
handle_error() {
    echo "ERROR: $1"
    exit 1
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options] <input_file>"
    echo "Options:"
    echo "  -o, --output <file>    Specify output file name"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 document.docx                 # Convert Word to Markdown"
    echo "  $0 document.md                   # Convert Markdown to Word"
    echo "  $0 -o custom_name.md document.docx  # Specify output filename"
    exit 0
}

# Function to check if pandoc is installed
check_pandoc() {
    command -v pandoc &> /dev/null || handle_error "Pandoc is not installed. Please install it first."
}

# Function to check if a file exists and handle overwriting
check_file_exists() {
    local output_file="$1"
    if [ -f "$output_file" ]; then
        read -p "File '$output_file' already exists. Overwrite? (y/n): " answer
        if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
            local dir=$(dirname -- "$output_file")
            local filename=$(basename -- "$output_file")
            local base_name="${filename%.*}"
            local extension="${output_file##*.}"
            [ "$base_name" = "$extension" ] && extension="" || extension=".$extension"
            local counter=1
            while [ -f "${dir}/${base_name}_${counter}${extension}" ]; do
                ((counter++))
            done
            output_file="${dir}/${base_name}_${counter}${extension}"
            echo "Using new filename: $output_file" >&2
        fi
    fi
    echo "$output_file"
}

# Function to detect if a file is markdown
is_markdown() {
    grep -qE "^(#|##|###|\*\*.*\*\*|[-*+]\s|\[.*\]\(.*\)|>\s)" "$1" && return 0 || return 1
}

# Helper function to resolve paths and generate output filenames
resolve_output_file() {
    local input_file="$1"
    local output_file="$2"
    local extension="$3"
    input_file=$(realpath "$input_file")
    if [ -z "$output_file" ]; then
        local dir=$(dirname -- "$input_file")
        local base_name="${input_file%.*}"
        output_file="${dir}/${base_name##*/}.${extension}"
    else
        # Ensure output_file is resolved relative to the input file's directory if not absolute
        if [[ "$output_file" != /* ]]; then
            local dir=$(dirname -- "$input_file")
            output_file="${dir}/$(basename -- "$output_file")"
        fi
        output_file=$(realpath "$output_file")
    fi
    echo "$(check_file_exists "$output_file")"
}

# Function to convert Word to Markdown
word_to_markdown() {
    local input_file="$1"
    local output_file=$(resolve_output_file "$1" "$2" "md")
    pandoc -s "$input_file" -o "$output_file" || handle_error "Conversion failed"
}

# Function to convert Markdown to Word
markdown_to_word() {
    local input_file="$1"
    local output_file=$(resolve_output_file "$1" "$2" "docx")
    pandoc -s "$input_file" -o "$output_file" || handle_error "Conversion failed"
}

# Main function
main() {
    check_pandoc
    local output_file=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -o|--output)
                [[ -n "$2" && "$2" != -* ]] || handle_error "Output file name is missing after $1"
                output_file="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                ;;
            -*)
                handle_error "Unknown option: $1"
                ;;
            *)
                break
                ;;
        esac
    done
    [[ $# -eq 0 ]] && handle_error "No file specified. Usage: $0 [options] <filename>"
    local input_file=$(realpath "$1")
    [[ -f "$input_file" ]] || handle_error "File '$input_file' does not exist"
    local extension=$(echo "${input_file##*.}" | tr '[:upper:]' '[:lower:]')
    case "$extension" in
        docx|doc|odt) word_to_markdown "$input_file" "$output_file" ;;
        md|markdown|txt) markdown_to_word "$input_file" "$output_file" ;;
        *)
            echo "No clear file extension. Attempting to detect file type..."
            if is_markdown "$input_file"; then
                echo "File appears to be Markdown."
                markdown_to_word "$input_file" "$output_file"
            else
                echo "File does not appear to be Markdown. Assuming it's a Word document."
                word_to_markdown "$input_file" "$output_file"
            fi
            ;;
    esac
}

# Run the main function
main "$@"