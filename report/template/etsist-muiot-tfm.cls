%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%  ETSIST/ETSISI MUIoT class for LaTeX files      2026-05-18
%%  For any information, please send an e-mail to:
%%          nestor.lucas@upm.es (Néstor Lucas Martínez)
%%          estela.mora.barba@upm.es (Estela Mora Barba)
%%
%%  License: MIT License 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand\fileversion{2.1.0}
\newcommand\filedate{2026/05/18}
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{etsist-muiot-tfm}[\filedate\space MUIoT TFM template class (v\fileversion)]
\typeout{MUIoT Master Thesis - ETSIST Spacing + Thesis.cls Chapters}

%% INDEX & ACRONYMS
\newif\ifPFG@index\PFG@indexfalse
\DeclareOption{index}{\PFG@indextrue}
\newif\ifPFG@acronyms\PFG@acronymsfalse
\DeclareOption{acronyms}\PFG@acronymstrue

%% PRE-DEFINED OPTIONS
\DeclareOption{10pt}{\PassOptionsToClass{10pt}{book}}
\DeclareOption{11pt}{\PassOptionsToClass{11pt}{book}}
\DeclareOption{12pt}{\PassOptionsToClass{12pt}{book}}

\newcommand\PFG@papersize{a4paper}
\DeclareOption{a4paper}{\renewcommand\PFG@papersize{a4paper}}
\PassOptionsToClass{\PFG@papersize}{book}

%% LANGUAGE
\newcommand{\doclanguage}{en} 
\DeclareOption{spanish}{
    \ClassWarning{etsist-muiot-tfm}{Spanish language is disabled for MIoT TFM. Forcing English.}
}
\DeclareOption{english}{\renewcommand{\doclanguage}{en}}

%% PRINT / DIGITAL INITIALIZATION
\newif\ifprintversion\printversionfalse
\DeclareOption{print}{\printversiontrue}
\DeclareOption{digital}{\printversionfalse}

\ExecuteOptions{11pt}
\ProcessOptions\relax

\ifprintversion
    \PassOptionsToClass{openright}{book}
\else
    \PassOptionsToClass{openany}{book}
\fi
\LoadClass{book}

% --------------------------------------------------------
% GLOBAL LAYOUT ADJUSTMENTS
% --------------------------------------------------------
\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{3}
\raggedbottom
\sloppy 
% --------------------------------------------------------

%% FONTS
\RequirePackage{fontspec}
\RequirePackage{lmodern}
\RequirePackage[usenames, dvipsnames]{color}
\setmainfont{Arial} 

%% PACKAGES
\RequirePackage{lscape}
\RequirePackage{setspace}
\RequirePackage{calc}
\RequirePackage{soul}
\RequirePackage{float}
\RequirePackage{emptypage}
\RequirePackage{ifthen}
\RequirePackage{ifpdf}
\RequirePackage{ifxetex}
\RequirePackage{titlesec}
\RequirePackage[nottoc]{tocbibind}
\RequirePackage[title,titletoc]{appendix}
\RequirePackage[titles]{tocloft} 
\RequirePackage{caption}
\RequirePackage{tablefootnote}
\RequirePackage{tabularx}
\RequirePackage{enumitem}
\RequirePackage{graphicx} 
\RequirePackage{pdfpages}
\RequirePackage{array}
\RequirePackage[none]{hyphenat}

% ESPACIOS ORIGINALES DE LA PLANTILLA ETSIST-PFG
\setlength{\parindent}{0pt} % No indentation for paragraphs
\setlength{\parskip}{1ex}   % Adjust vertical space between paragraphs

\soulregister\cite7\soulregister\ref7\soulregister\label7

%% DYNAMIC PRINT/DIGITAL TOGGLES
\let\originalcleardoublepage\cleardoublepage

\newcommand{\forceRightPage}{\clearpage}

\newcommand{\setprintversion}{
    \printversiontrue
    \let\cleardoublepage\originalcleardoublepage
    \renewcommand{\forceRightPage}{\clearpage\ifodd\value{page}\else\null\thispagestyle{empty}\newpage\fi}
}

\newcommand{\setdigitalversion}{
    \printversionfalse
    \let\cleardoublepage\clearpage
    \renewcommand{\forceRightPage}{\clearpage}
}

\ifprintversion
    \setprintversion
\else
    \setdigitalversion
\fi

%% METADATA COMMANDS
\def\@degree{}
\def\@department{}
\def\@tutor{}
\def\@director{}

\newcommand{\degree}[1]{\def\@degree{#1}}  
\renewcommand{\author}[2][male]{%
    \def\@author{#2}% 
    \def\@authorGender{#1}% 
}
\newcommand{\director}[2][male]{%
    \def\@director{#2}% 
    \def\@directorGender{#1}% 
}
\newcommand{\tutor}[2][male]{%
    \def\@tutor{#2}% 
    \def\@tutorGender{#1}% 
}
\newcommand{\department}[1]{\def\@department{#1}}  
\newcommand{\authorGender}[1]{\def\@authorGender{#1}}  

%% LANGUAGE & QUOTES
\RequirePackage[english]{babel}
\RequirePackage{csquotes}
\newcommand{\titlestring}{TITLE}

%% LIST OF EQUATIONS
\newcommand{\listequationsname}{List of Equations}
\newlistof{equations}{loe}{\listequationsname}
\setlength{\cftequationsnumwidth}{3.5em}
\newcommand{\addequation}[1]{%
  \addcontentsline{loe}{equations}{\protect\numberline{(\theequation)}#1}\ignorespaces%
}

\let\originallistofequations\listofequations
\renewcommand{\listofequations}{
    \cleardoublepage
    \ifdefined\phantomsection\phantomsection\fi
    \addcontentsline{toc}{chapter}{\listequationsname}
    \originallistofequations
}

\addto\captionsenglish{
    \renewcommand{\contentsname}{Table of Contents}
    \renewcommand{\listfigurename}{List of Figures}
    \renewcommand{\listtablename}{List of Tables}
    \renewcommand{\listequationsname}{List of Equations}
}

%% CAPTIONS (Originales de la plantilla etsist-pfg)
\captionsetup[table]{position=above}
\captionsetup{skip=1em}

\RequirePackage{xcolor}
\RequirePackage{booktabs}

%% CHAPTER AND SECTION FORMATTING
% Formato de capítulos clásico (Thesis.cls)
\titleformat{\chapter}[display]
  {\normalfont\huge\bfseries}
  {\chaptertitlename\ \thechapter}
  {20pt}
  {\Huge}
\titlespacing*{\chapter}{0pt}{50pt}{40pt}

% Formato de secciones (etsist-pfg)
\titlespacing{\section}{0pt}{*2}{*1}
\titlespacing{\subsection}{0pt}{*1.5}{*0.8}
\titlespacing{\subsubsection}{0pt}{*1.2}{*0.6}

%% HYPERREF
\RequirePackage[unicode=true]{hyperref}

\ifprintversion 
    \hypersetup{
        final=true, plainpages=false, pdfstartview=FitV, pdftoolbar=true, pdfmenubar=true,
        bookmarksopen=true, bookmarksnumbered=true, breaklinks=true, linktocpage,
        colorlinks=true, linkcolor=black, urlcolor=black, citecolor=black, anchorcolor=black
    }
    \RequirePackage[paper=\PFG@papersize, hmarginratio=2:3, bindingoffset=10mm, marginparwidth=2cm, inner=2cm, outer=2cm, top=3cm, bottom=3cm]{geometry}
\else 
    \hypersetup{
        final=true, plainpages=false, pdfstartview=FitV, pdftoolbar=true, pdfmenubar=true,
        bookmarksopen=true, bookmarksnumbered=true, breaklinks=true, linktocpage,
        colorlinks=true, linkcolor=blue, urlcolor=blue, citecolor=blue, anchorcolor=green
    }
    \RequirePackage[paper=\PFG@papersize, hmarginratio=2:3, vmarginratio=1:1, scale=0.75, bindingoffset=10mm]{geometry}
    \hypersetup{pdfpagelayout=OneColumn}
\fi

%% PDF META-DATA 
\AtBeginDocument{
    \hypersetup{
        pdftitle = {\@title},
        pdfauthor = {\@author},
        pdfsubject = {\@degree \ - \@department}
    }
}

%% TOC & HEADERS
\newcommand{\nocontentsline}[3]{}
\newcommand{\tochide}[2]{\bgroup\let\addcontentsline=\nocontentsline#1{#2}\egroup}

\addtocontents{toc}{\protect\thispagestyle{empty}}

\RequirePackage{fancyhdr} 
\fancyhf{}
\renewcommand{\chaptermark}[1]{\markboth{#1}{}}
\fancyhead[RO]{\textit{\leftmark}} 
\fancyhead[LE]{\textit{\leftmark}} 
\fancyfoot[RO]{\thepage} 
\fancyfoot[LE]{\thepage} 
\pagestyle{fancy}
\setlength{\headheight}{14.5pt}

\fancypagestyle{plain}{
	\fancyhead{} 
	\renewcommand{\headrulewidth}{0pt}
}

\newcommand{\frontmattersection}{
    \clearpage
    \ifprintversion \forceRightPage \fi
}

%% ACRONYMS
\RequirePackage[toc,acronym,nonumberlist,nogroupskip]{glossaries}
\makeglossaries
\setglossarystyle{alttree}
\glssetwidest{XXXXXXXXXX}
\newcommand{\printacronyms}{
    \cleardoublepage
    \printglossary[type=\acronymtype]
}

%% BIBLIOGRAPHY
% biblatex: 'iso8601' is deprecated; use 'iso'. Also keep 'seconds=true' to satisfy
% biblatex's requirements when using ISO dates in urldate.
%
% TL2025 + biblatex-ieee can emit:
%   "Package biblatex Warning: Macro 'volume+number' undefined. Using \newbibmacro."
% It's harmless, but we filter it to keep the build log clean.
\RequirePackage{silence}
\WarningFilter[biblatex]{biblatex}{Macro 'volume+number' undefined}

\RequirePackage[backend=biber,style=ieee,sorting=none,urldate=iso,seconds=true,maxnames=4]{biblatex}

% Define the macro anyway (in case the style uses it later).
\providebibmacro{volume+number}{%
  \printfield{volume}%
  \iffieldundef{number}{}{%
    \setunit*{\addnbspace}%
    \printfield{number}%
  }%
}

%% ACKNOWLEDGEMENTS & SUMMARY
\newenvironment{acknowledgements} {
  \cleardoublepage
  \ifdefined\phantomsection\phantomsection\fi
  \addcontentsline{toc}{chapter}{Acknowledgements}
  \chapter*{Acknowledgements}
  \thispagestyle{empty}
}

\newenvironment{summary} {
  \cleardoublepage
  \ifdefined\phantomsection\phantomsection\fi
  \addcontentsline{toc}{chapter}{Summary}
  \chapter*{Summary}
  \thispagestyle{empty}
}

\endinput