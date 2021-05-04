import os
import re 
import io
import numpy as np
import pickle
from elasticsearch import Elasticsearch
from ranker2 import *
from gensim import corpora, models, similarities
from gensim.parsing.preprocessing import remove_stopwords, preprocess_string
from collections import defaultdict

main_path = os.path.dirname(os.path.realpath(__file__))
static_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'static')
slides_path = os.path.join(main_path,'pdf.js/static/slides')
related_slides_path = os.path.join(static_path,'ranking_results.csv')
vocab_path = os.path.join(static_path,'tf_idf_outputs','vocabulary_list.p')
tfidfs_path = os.path.join(static_path,'tf_idf_outputs','normalized_tfidfs.npy')
title_tfidfs_path =  os.path.join(static_path,'tf_idf_outputs','normalized_title_tfidfs.npy')
ss_corpus_path = os.path.join(static_path,'tf_idf_outputs','ss_corpus.p')
word2vec_path = os.path.join(static_path,'word2vec_model')
paras_folder = os.path.join(main_path,'para_idx_data')
cfg = os.path.join(main_path,'para_idx_data','config.toml')
word2vec = pickle.load(open(word2vec_path, 'rb'))

related_dict = {}
slide_names = open(os.path.join(static_path,'slide_names2.txt'), 'r').readlines()
slide_names = [name.strip() for name in slide_names]
slide_titles = io.open(os.path.join(static_path,'slide_titles.txt'), 'r', encoding='utf-8').readlines()
slide_titles = [t.strip() for t in slide_titles]
title_mapping = dict(zip(slide_names, slide_titles))
print('Building or loading index...')
idx = metapy.index.make_inverted_index(cfg)
mu = 2500
alpha = 0.34
ranker_obj = load_ranker(cfg,mu)

with open(cfg, 'r') as fin:
    cfg_d = pytoml.load(fin)

vocabulary_list = pickle.load(open(vocab_path, 'rb'))
tfidfs = np.load(tfidfs_path)
title_tfidfs = np.load(title_tfidfs_path)
ss_corpus = pickle.load(open(ss_corpus_path, 'rb'))

log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'log','log.txt')
es = Elasticsearch()


def log(ip,to_slide,action,start_time):
    with open(log_path,'a+') as f:
        f.write('{},{},{},{}\n'.format(ip,to_slide,action,start_time))
        
def get_snippet_sentences(slide_name, matching_keywords):
    idx = slide_names.index(slide_name)
    content = ss_corpus[idx].split(' ')
    include  = [0]*len(content)
    for c in range(len(content)):
        if content[c] in matching_keywords:
            for i in range(max(0,c-2), min(c+3,len(content))):
                include[i] = 1
    text = '' 
    for c in range(len(content)):
        if include[c]== 1:
            if c!=0 and include[c-1] == 0:
                text += '......'
            text += content[c] + ' '
    text += '......'
    return text

def trim_name(slide_name):
    name = slide_name.split(' ')
    new_name = []
    
    for i,n in enumerate(name):
        if (len(re.findall('[0-9\.]+', n)) != 0 and i>0 and name[i-1].lower()=='part') or (len(re.findall('[0-9\.]+', n)) == 0):

            if (n == 'Lesson') or (n in new_name) or (len(re.findall('[0-9\.]+', n)) == 0 and len(n)<=2) :
                continue
            new_name += [n]
        
           

    return ' '.join(new_name)

def get_color(slide_course_name, related_slide_course_name):
    if slide_course_name==related_slide_course_name:
        return "blue"
    else:
        return "brown"

def get_snippet(slide_name, related_slide_name):
    no_keywords = False
    related_slide_name = related_slide_name.replace('----', '##')[:-4]
    slide_name = slide_name.replace('----', '##')[:-4]
    idx1 = slide_names.index(slide_name)
    idx2 = slide_names.index(related_slide_name)    
    title_tfidf1 = title_tfidfs[idx1,:]
    title_tfidf2 = title_tfidfs[idx2,:]
    tfidf1 = tfidfs[idx1,:]
    tfidf2 = tfidfs[idx2,:]
    term_sims = 2.8956628*(title_tfidf1*title_tfidf2)+ 5.92724651*(tfidf1*tfidf2)
    top_terms_indeces = np.argsort(term_sims)[::-1][:5]
    #print related_slide_name
    #print np.sort(term_sims)[::-1][:10]
    top_terms_indeces = filter(lambda l : term_sims[l]>0, top_terms_indeces)
    matching_words = [vocabulary_list[t] for t in top_terms_indeces]
    #matching_words = [(vocabulary_list[t],vec.idf_[t]) for t in top_terms_indeces]
    #matching_words = sorted(matching_words, key = lambda l :l[1], reverse = True)
    #matching_words = map(lambda l : l[0], matching_words)
    if len(matching_words) == 0 :
        no_keywords = True
    keywords = ', '.join(matching_words) 
    snippet_sentence =  get_snippet_sentences(related_slide_name, matching_words)

    return (('Slide title : ' + title_mapping[related_slide_name][:-1] +'\n' + 'Matching keywords: ' + keywords + '\n' + 'Snippet:' + snippet_sentence),no_keywords)

# idx = metapy.index.make_inverted_index('slides-config.toml')
# ranker = metapy.index.OkapiBM25()
# slide_titles = []
# with open(os.path.join('./slides/slides.dat.labels')) as f:
#     for line in f:
#         slide_titles.append(line[:-1])

def get_course_names():
    course_names = sorted(os.listdir(slides_path))
    cn_cpy = list(course_names)
    for cn in cn_cpy:
        if cn!='cs-410':
            course_names.remove(cn)
    num_course = len(course_names)
    return course_names,num_course


def load_related_slides():
    global related_dict
    with open(related_slides_path,'r') as f:
        related_slides = f.readlines()
    for row in related_slides:
        cols = row.split(',')
        key = cols[0].replace('##','----')+'.pdf'
        related_dict[key] = []
        for col_num in range(1,len(cols),2):
            pdf_name = cols[col_num].replace('##','----')+'.pdf'
            if cols[col_num+1].strip() != '':
                score = float(cols[col_num+1].strip())
                if score < 0.03:
                    break
            name_comp = pdf_name.split('----')
            course_name = name_comp[0]
            if course_name != 'cs-410':
                continue
            lec_name ='----'.join(name_comp[1:-1])
            if os.path.exists(os.path.join(slides_path,course_name,lec_name,pdf_name)):
                related_dict[key].append(pdf_name)

def sort_slide_names(l): 
    """ Sort the given iterable in the way that humans expect.""" 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

def get_lectures_from_course(course_name):
    return sort_slide_names(os.listdir(os.path.join(slides_path, course_name)))

def get_slide(course_name,slide,lno):
    lectures = get_lectures_from_course(course_name)
    lno = int(lno)
    ses_disp_str = get_disp_str(slide)
    related_slides_info = get_related_slides(slide)
    same_lecture_slides_info = get_same_lecture_slides(course_name, lno, slide)
    return slide,lno,lectures[lno],related_slides_info,lectures,range(len(lectures)),ses_disp_str,same_lecture_slides_info

def get_same_lecture_slides(course_name, lno, slide_name):
    lectures = get_lectures_from_course(course_name)
    lno = int(lno)
    slides = sort_slide_names(os.listdir(os.path.join(slides_path,course_name,lectures[lno])))
    return get_snippets_info_of_slides(slide_name, slides, False)

def get_disp_str(slide_name):
    slide_no = slide_name.split('----')[-1][:-4].title()
    comp = slide_name.split('----')
    slide_name = ' '.join(comp[-2].replace('.txt','').replace('_','-').split('-')).title() 
    return ' '.join(comp[0].replace('_','-').split('-')).title() + ' : ' + trim_name(slide_name) + ', ' +slide_no 

def get_next_slide(course_name,lno,curr_slide=None):
    lectures = get_lectures_from_course(course_name)
    lno = int(lno)
    slides = sort_slide_names(os.listdir(os.path.join(slides_path,course_name,lectures[lno])))
    if curr_slide is not None:
        idx = slides.index(curr_slide)
        slides = slides[idx+1:]
    if len(slides)>0:
        next_slide = slides[0]
    else:
        if lno==len(lectures)-1:
            return None,None,None,(None,None,None,None,None,None,None,None),None,None,None
        else:
            next_slide = sort_slide_names(os.listdir(os.path.join(slides_path,course_name,lectures[lno+1])))[0]
            lno+=1
    return get_slide(course_name, next_slide, lno)

def get_prev_slide(course_name,lno,curr_slide):
    lectures = get_lectures_from_course(course_name)
    lno = int(lno)
    slides = sort_slide_names(os.listdir(os.path.join(slides_path,course_name,lectures[lno])))
    idx = slides.index(curr_slide)
    if idx==0:
            if lno==0:
                return None,None,None,(None,None,None,None,None,None,None,None),None,None,None
            else:
                prev_slide = sort_slide_names(os.listdir(os.path.join(slides_path,course_name,lectures[lno-1])))[-1]
                lno-=1
    else:
        prev_slide = slides[:idx][-1]
    return get_slide(course_name, prev_slide, lno)

def get_slide_snippet_information(slide, slide_comp, slide_name):
            comp = slide.split('----')
            course_name = slide_comp[0]
            related_slide_name = ' '.join(comp[-2].replace('.txt','').replace('_','-').split('-')).title() 
            slide_course_name = ' '.join(course_name.replace('_','-').split('-')).title()
            related_slide_course_name = ' '.join(course_name.replace('_','-').split('-')).title()
            trimmed_name = ' '.join(course_name.replace('_','-').split('-')).title() + ' : ' + trim_name(related_slide_name)
            color = get_color(slide_course_name, related_slide_course_name)
            lname = '----'.join(comp[1:-1])
            disp_str = ' '.join(course_name.replace('_','-').split('-')).title() + ' : ' + trim_name(related_slide_name)
            return lname, disp_str, color, course_name, trimmed_name

def get_snippets_info_of_slides(slide_name, slides, call_by_related=True):
    filtered_related_slides = []
    disp_strs = []
    disp_colors = []
    disp_snippets= []
    course_names = []
    lnos = []
    slide_comp = slide_name.split('----')
    related_slide_trim_names = []
    lec_names = []
    if len(slides) > 0:
        filtered_related_slides = []
        for r in slides:
            res = get_slide_snippet_information(r, slide_comp, slide_name)
            if res == None:
                continue
            lname, disp_str, color, course_name, trimmed_name = res 
            snippet,no_keywords = get_snippet(slide_name, r)
            if no_keywords==True and call_by_related:
                continue
            if trimmed_name in related_slide_trim_names and call_by_related:
                continue
            else:
                related_slide_trim_names.append(trimmed_name)
            lectures = get_lectures_from_course(course_name)
            lnos.append(lectures.index(lname))
            lec_names.append(lname)
            filtered_related_slides.append(r)
            disp_strs.append(disp_str)
            disp_snippets.append(snippet)
            disp_colors.append(color)
            course_names.append(course_name)
    else:
        filtered_related_slides = []
    return len(disp_strs),filtered_related_slides,disp_strs,course_names,lnos,lec_names,disp_colors,disp_snippets


def get_related_slides(slide_name):
    if related_dict=={}:
        load_related_slides()
    related_slides = []
    if slide_name in related_dict:
        related_slides = related_dict[slide_name]
    return get_snippets_info_of_slides(slide_name, related_slides)

def format_string(matchobj):
    
    return '<span style="background-color: #bddcf5">'+matchobj.group(0)+'</span>'

def get_search_results(search):
    top_docs = []
    res = es.search(index='slides',body={"query":{'match':{'content':search}}},size=50)
    # print(res)
    for d in res['hits']['hits']:
        top_docs.append(d[u'_source'][u'label'])
    
    results = []
    disp_strs = []
    course_names = []
    snippets = []
    lnos = []
    top_slide_trim_names = []
    lec_names = []
    for r in top_docs:

            comp = r.split('##')
            
            lectures = get_lectures_from_course(comp[0])
            lname = '----'.join(comp[1:-1])
            try:
                lnos.append(lectures.index(lname))
            except ValueError: #not an "actual" slide
                continue

            if len(results) < 10:
                disp_strs.append(' '.join(comp[0].replace('_','-').split('-')).title() + ' : ' + trim_name(' '.join(comp[-2].replace('.txt','').replace('_','-').split('-')).title() )+ ', ' + ' '.join(comp[-1].replace('.pdf','').split('-')).title())
                course_names.append(comp[0])
                lec_names.append(lname)
            
                results.append(r)
                snippets.append(get_snippet_sentences(r, search))
        
    for x in range(len(results)):
        results[x] = results[x].replace('##', '----') + '.pdf'
    return len(results),results,disp_strs,course_names,lnos, snippets,lec_names

def get_explanation(search_string,top_k=1):
    query = metapy.index.Document()
    query.content(search_string)
    documents = score2(ranker_obj, query, top_k, alpha)

    explanation = []
    file_names = []
    for doc in documents:
        with open(os.path.join(paras_folder, doc), "r") as f:
            explanation.append(f.read().strip())
            print(explanation)
            file_names.append(doc)

    return explanation, file_names
    query = metapy.index.Document()
    query.content(search_string)
    print(f"get_explanation: {search_string}")
    # score2(ranker,idx,query)
    file_id_tups, fn_dict = score2(ranker_obj,idx,query,top_k,alpha)
    # print(file_id_tups,fn_dict)
    explanation = ''
    file_names = []
    for fn,_ in sorted(fn_dict.items(),key=lambda k :k[1],reverse=True)[:top_k]:
        with open(os.path.join(paras_folder,fn),'r') as f:
            explanation += f.read().strip()
            file_names.append(fn)
    formatted_exp = explanation
    for w in search_string.lower().split():
        (sub_str,cnt) = re.subn(re.compile(r"\b{}\b".format(w),re.I),format_string,formatted_exp)
        if cnt>0:
            formatted_exp = sub_str
    return formatted_exp,'#'.join(file_names)

def get_vector_similarity(vA, vB):
    return np.dot(vA, vB) / (np.sqrt(np.dot(vA,vA)) * np.sqrt(np.dot(vB,vB)))


def rank_google_result(raw_results, context, query):
    print([x['title'] for x in raw_results])
    documents = list(map(lambda x: " ".join([x['title'], x['snippet']]), raw_results))
    documents = list(map(lambda x: preprocess_string(x), documents))
    
    documents_vectors = list(map(get_sent_vector, documents))
    context_vector = get_context_vector(context, query)
    similarities = []
    if context_vector is None:
        return [i for i in range(len(raw_results))]
    else:
        similarities = list(map(lambda x: get_vector_similarity(x, context_vector), documents_vectors))
    keyword_counts = list(map(lambda x: count_keyword_match(x['title'], query), raw_results))
    return get_ranking_index(similarities, keyword_counts)

def split_to_words(sent):
    return list(filter(lambda x: len(x) > 3, re.findall(r"[\w']+", sent)))

def get_vec_from_word(w):
    try:
        return word2vec[w]
    except KeyError:
        return None

def count_keyword_match(title, query):
    title_words = split_to_words(title.lower()) 
    query_words = split_to_words(query.lower()) 
    title_vecs = [get_vec_from_word(x) for x in title_words]
    query_vecs = [get_vec_from_word(x) for x in query_words]
    count = 0
    for v1 in title_vecs:
        if v1 is None:
            continue
        for v2 in query_vecs:
            if v2 is None:
                continue
            if get_vector_similarity(v1, v2) > 0.5:
                count += 1
    print(title, count)
    return count / len(title_words)


def get_ranking_index(similarities, keyword_counts):
    for i in range(len(similarities)):
        print(similarities[i], keyword_counts[i])
    scores = [similarities[i] + keyword_counts[i] for i in range(len(similarities))]
    return np.argsort(scores)[::-1]

def get_sent_vector(sent):
    accus = []
    count = 0
    for w in sent:
        try:
            v = word2vec[w.lower()]
            accus.append(v)
        except KeyError:
            continue
    return np.mean(accus, axis=0) if len(accus) else None

def get_context_vector(context, query):
    query_vec = get_sent_vector(split_to_words(query))
    if query_vec is None:
        return None
    vecs = []
    for w in split_to_words(context):
        try:
            w_vec = word2vec[w]
            sim = get_vector_similarity(w_vec, query_vec)
            print(sim, w)
            if sim > 0.1:
                vecs.append(w_vec)
        except KeyError:
            continue
    return np.mean(vecs, axis=0) if len(vecs) > 0 else query_vec

