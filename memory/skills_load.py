#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Loader Module
用于加载指定文件夹下的所有skill，并返回skill信息字符串
"""

import os
import re
from typing import List, Dict, Optional


def parse_skill_frontmatter(file_path: str) -> Optional[Dict[str, str]]:
    """
    解析SKILL.md文件的YAML frontmatter
    
    Args:
        file_path: SKILL.md文件路径
        
    Returns:
        包含skill信息的字典，如果解析失败则返回None
    """
    try:

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配YAML frontmatter（在---分隔符之间）
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.search(frontmatter_pattern, content, re.DOTALL | re.MULTILINE)
        
        if not match:
            return None
        
        frontmatter_text = match.group(1)
        
        # 将frontmatter按行分割
        lines = frontmatter_text.split('\n')
        
        # 解析YAML frontmatter中的name和description字段
        skill_info = {}
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 提取name字段
            if line.startswith('name:'):
                skill_info['name'] = line.split(':', 1)[1].strip()
            
            # 提取description字段（可能有多行）
            elif line.startswith('description:'):
                # 收集后续的所有缩进行（以空格或制表符开头）
                desc_lines = []
                i += 1  # 移动到下一行
                while i < len(lines) and (lines[i].startswith('  ') or lines[i].startswith('\t')):
                    desc_lines.append(lines[i].strip())
                    i += 1
                
                if desc_lines:
                    skill_info['description'] = ' '.join(desc_lines)
                continue  # 已经增加了i，所以跳过下面的i += 1
            
            i += 1
        
        return skill_info if skill_info else None
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def find_skill_files(skills_dir: str) -> List[str]:
    """
    查找指定目录下的所有SKILL.md文件
    
    Args:
        skills_dir: skills目录路径
        
    Returns:
        SKILL.md文件路径列表
    """
    skill_files = []
    
    for root, dirs, files in os.walk(skills_dir):
        for file in files:
            if file == 'SKILL.md':
                skill_files.append(root)
    
    return skill_files


def load_skills(skills_dir: str) -> str:
    """
    加载指定文件夹下的所有skill，返回格式化的字符串
    
    Args:
        skills_dir: skills目录路径
        
    Returns:
        包含所有skill信息的格式化字符串
    """
    if not os.path.exists(skills_dir):
        return f"Error: Skills directory '{skills_dir}' does not exist."
    
    if not os.path.isdir(skills_dir):
        return f"Error: '{skills_dir}' is not a directory."
    
    skill_files = find_skill_files(skills_dir)
    
    if not skill_files:
        return f"No SKILL.md files found in '{skills_dir}'."
    
    # 收集所有skill信息
    skills_info = []
    
    for skill_file in skill_files:
        skill_info = parse_skill_frontmatter(os.path.join(skill_file, "SKILL.md"))
        if skill_info:
            # 获取相对路径
            skill_info['path'] = os.path.join(skill_file, "SKILL.md")
            skills_info.append(skill_info)
    
    if not skills_info:
        return f"Found {len(skill_files)} SKILL.md files, but could not parse any frontmatter."
    
    # 格式化输出字符串
    describe_message = "以下是技能清单，以及相应的描述与实际路径。如果需要执行某个技能，使用 read_file 读取对应path获取完整的技能流程。"
    output_lines = []
    output_lines.append(describe_message)
    
    for i, skill in enumerate(skills_info, 1):
        output_lines.append(f"\n{i}. Skill: {skill.get('name', 'Unknown')}")
        output_lines.append(f"   Path: {skill.get('path', 'Unknown')}")
        
        description = skill.get('description', 'No description available')
        # 如果描述太长，适当换行
        if len(description) > 100:
            # 简单换行逻辑：每100个字符换行
            wrapped_desc = []
            for j in range(0, len(description), 100):
                wrapped_desc.append(description[j:j+100])
            desc_lines = '\n     '.join(wrapped_desc)
            output_lines.append(f"   Description: {desc_lines}")
        else:
            output_lines.append(f"   Description: {description}")
        
    

    return '\n'.join(output_lines)

