"""
polymorphism does not work with pydantic and the schema.org models
so we cannot just use define as field as type "Parent" and have it
accept any subclass of Parent

FIXME: think about optimizations here. This takes forever to import
"""

from typing import Union

from pydantic2_schemaorg.APIReference import APIReference
from pydantic2_schemaorg.AboutPage import AboutPage
from pydantic2_schemaorg.AdvertiserContentArticle import AdvertiserContentArticle
from pydantic2_schemaorg.AmpStory import AmpStory
from pydantic2_schemaorg.AnalysisNewsArticle import AnalysisNewsArticle
from pydantic2_schemaorg.Answer import Answer
from pydantic2_schemaorg.ArchiveComponent import ArchiveComponent
from pydantic2_schemaorg.Article import Article
from pydantic2_schemaorg.AskPublicNewsArticle import AskPublicNewsArticle
from pydantic2_schemaorg.Atlas import Atlas
from pydantic2_schemaorg.AudioObject import AudioObject
from pydantic2_schemaorg.AudioObjectSnapshot import AudioObjectSnapshot
from pydantic2_schemaorg.Audiobook import Audiobook
from pydantic2_schemaorg.BackgroundNewsArticle import BackgroundNewsArticle
from pydantic2_schemaorg.Barcode import Barcode
from pydantic2_schemaorg.Blog import Blog
from pydantic2_schemaorg.BlogPosting import BlogPosting
from pydantic2_schemaorg.Book import Book
from pydantic2_schemaorg.BookSeries import BookSeries
from pydantic2_schemaorg.CategoryCodeSet import CategoryCodeSet
from pydantic2_schemaorg.Certification import Certification
from pydantic2_schemaorg.Chapter import Chapter
from pydantic2_schemaorg.CheckoutPage import CheckoutPage
from pydantic2_schemaorg.Claim import Claim
from pydantic2_schemaorg.ClaimReview import ClaimReview
from pydantic2_schemaorg.Clip import Clip
from pydantic2_schemaorg.Code import Code
from pydantic2_schemaorg.Collection import Collection
from pydantic2_schemaorg.CollectionPage import CollectionPage
from pydantic2_schemaorg.ComicCoverArt import ComicCoverArt
from pydantic2_schemaorg.ComicIssue import ComicIssue
from pydantic2_schemaorg.ComicSeries import ComicSeries
from pydantic2_schemaorg.ComicStory import ComicStory
from pydantic2_schemaorg.Comment import Comment
from pydantic2_schemaorg.CompleteDataFeed import CompleteDataFeed
from pydantic2_schemaorg.ContactPage import ContactPage
from pydantic2_schemaorg.Conversation import Conversation
from pydantic2_schemaorg.CorrectionComment import CorrectionComment
from pydantic2_schemaorg.Course import Course
from pydantic2_schemaorg.CoverArt import CoverArt
from pydantic2_schemaorg.CreativeWorkSeason import CreativeWorkSeason
from pydantic2_schemaorg.CreativeWorkSeries import CreativeWorkSeries
from pydantic2_schemaorg.CriticReview import CriticReview
from pydantic2_schemaorg.DataCatalog import DataCatalog
from pydantic2_schemaorg.DataDownload import DataDownload
from pydantic2_schemaorg.DataFeed import DataFeed
from pydantic2_schemaorg.Dataset import Dataset
from pydantic2_schemaorg.DefinedTermSet import DefinedTermSet
from pydantic2_schemaorg.Diet import Diet
from pydantic2_schemaorg.DigitalDocument import DigitalDocument
from pydantic2_schemaorg.DiscussionForumPosting import DiscussionForumPosting
from pydantic2_schemaorg.Drawing import Drawing
from pydantic2_schemaorg.EducationalOccupationalCredential import (
    EducationalOccupationalCredential,
)
from pydantic2_schemaorg.EmailMessage import EmailMessage
from pydantic2_schemaorg.EmployerReview import EmployerReview
from pydantic2_schemaorg.Episode import Episode
from pydantic2_schemaorg.ExercisePlan import ExercisePlan
from pydantic2_schemaorg.FAQPage import FAQPage
from pydantic2_schemaorg.Game import Game
from pydantic2_schemaorg.Guide import Guide
from pydantic2_schemaorg.HealthTopicContent import HealthTopicContent
from pydantic2_schemaorg.HowTo import HowTo
from pydantic2_schemaorg.HowToDirection import HowToDirection
from pydantic2_schemaorg.HowToSection import HowToSection
from pydantic2_schemaorg.HowToStep import HowToStep
from pydantic2_schemaorg.HowToTip import HowToTip
from pydantic2_schemaorg.HyperToc import HyperToc
from pydantic2_schemaorg.HyperTocEntry import HyperTocEntry
from pydantic2_schemaorg.ImageGallery import ImageGallery
from pydantic2_schemaorg.ImageObject import ImageObject
from pydantic2_schemaorg.ImageObjectSnapshot import ImageObjectSnapshot
from pydantic2_schemaorg.ItemPage import ItemPage
from pydantic2_schemaorg.LearningResource import LearningResource
from pydantic2_schemaorg.Legislation import Legislation
from pydantic2_schemaorg.LegislationObject import LegislationObject
from pydantic2_schemaorg.LiveBlogPosting import LiveBlogPosting
from pydantic2_schemaorg.Manuscript import Manuscript
from pydantic2_schemaorg.Map import Map
from pydantic2_schemaorg.MathSolver import MathSolver
from pydantic2_schemaorg.MediaGallery import MediaGallery
from pydantic2_schemaorg.MediaObject import MediaObject
from pydantic2_schemaorg.MediaReview import MediaReview
from pydantic2_schemaorg.MediaReviewItem import MediaReviewItem
from pydantic2_schemaorg.MedicalScholarlyArticle import MedicalScholarlyArticle
from pydantic2_schemaorg.MedicalWebPage import MedicalWebPage
from pydantic2_schemaorg.Menu import Menu
from pydantic2_schemaorg.MenuSection import MenuSection
from pydantic2_schemaorg.Message import Message
from pydantic2_schemaorg.MobileApplication import MobileApplication
from pydantic2_schemaorg.Movie import Movie
from pydantic2_schemaorg.MovieClip import MovieClip
from pydantic2_schemaorg.MovieSeries import MovieSeries
from pydantic2_schemaorg.MusicAlbum import MusicAlbum
from pydantic2_schemaorg.MusicComposition import MusicComposition
from pydantic2_schemaorg.MusicPlaylist import MusicPlaylist
from pydantic2_schemaorg.MusicRecording import MusicRecording
from pydantic2_schemaorg.MusicRelease import MusicRelease
from pydantic2_schemaorg.MusicVideoObject import MusicVideoObject
from pydantic2_schemaorg.NewsArticle import NewsArticle
from pydantic2_schemaorg.Newspaper import Newspaper
from pydantic2_schemaorg.NoteDigitalDocument import NoteDigitalDocument
from pydantic2_schemaorg.OpinionNewsArticle import OpinionNewsArticle
from pydantic2_schemaorg.Painting import Painting
from pydantic2_schemaorg.Periodical import Periodical
from pydantic2_schemaorg.Photograph import Photograph
from pydantic2_schemaorg.Play import Play
from pydantic2_schemaorg.PodcastEpisode import PodcastEpisode
from pydantic2_schemaorg.PodcastSeason import PodcastSeason
from pydantic2_schemaorg.PodcastSeries import PodcastSeries
from pydantic2_schemaorg.Poster import Poster
from pydantic2_schemaorg.PresentationDigitalDocument import PresentationDigitalDocument
from pydantic2_schemaorg.ProductCollection import ProductCollection
from pydantic2_schemaorg.ProfilePage import ProfilePage
from pydantic2_schemaorg.PublicationIssue import PublicationIssue
from pydantic2_schemaorg.PublicationVolume import PublicationVolume
from pydantic2_schemaorg.QAPage import QAPage
from pydantic2_schemaorg.Question import Question
from pydantic2_schemaorg.Quiz import Quiz
from pydantic2_schemaorg.Quotation import Quotation
from pydantic2_schemaorg.RadioClip import RadioClip
from pydantic2_schemaorg.RadioEpisode import RadioEpisode
from pydantic2_schemaorg.RadioSeason import RadioSeason
from pydantic2_schemaorg.RadioSeries import RadioSeries
from pydantic2_schemaorg.RealEstateListing import RealEstateListing
from pydantic2_schemaorg.Recipe import Recipe
from pydantic2_schemaorg.Recommendation import Recommendation
from pydantic2_schemaorg.Report import Report
from pydantic2_schemaorg.ReportageNewsArticle import ReportageNewsArticle
from pydantic2_schemaorg.Review import Review
from pydantic2_schemaorg.ReviewNewsArticle import ReviewNewsArticle
from pydantic2_schemaorg.SatiricalArticle import SatiricalArticle
from pydantic2_schemaorg.ScholarlyArticle import ScholarlyArticle
from pydantic2_schemaorg.Sculpture import Sculpture
from pydantic2_schemaorg.SearchResultsPage import SearchResultsPage
from pydantic2_schemaorg.Season import Season
from pydantic2_schemaorg.SheetMusic import SheetMusic
from pydantic2_schemaorg.ShortStory import ShortStory
from pydantic2_schemaorg.SiteNavigationElement import SiteNavigationElement
from pydantic2_schemaorg.SocialMediaPosting import SocialMediaPosting
from pydantic2_schemaorg.SoftwareApplication import SoftwareApplication
from pydantic2_schemaorg.SoftwareSourceCode import SoftwareSourceCode
from pydantic2_schemaorg.SpecialAnnouncement import SpecialAnnouncement
from pydantic2_schemaorg.SpreadsheetDigitalDocument import SpreadsheetDigitalDocument
from pydantic2_schemaorg.Statement import Statement
from pydantic2_schemaorg.Syllabus import Syllabus
from pydantic2_schemaorg.TVClip import TVClip
from pydantic2_schemaorg.TVEpisode import TVEpisode
from pydantic2_schemaorg.TVSeason import TVSeason
from pydantic2_schemaorg.TVSeries import TVSeries
from pydantic2_schemaorg.Table import Table
from pydantic2_schemaorg.TechArticle import TechArticle
from pydantic2_schemaorg.TextDigitalDocument import TextDigitalDocument
from pydantic2_schemaorg.TextObject import TextObject
from pydantic2_schemaorg.Thesis import Thesis
from pydantic2_schemaorg.UserReview import UserReview
from pydantic2_schemaorg.VideoGallery import VideoGallery
from pydantic2_schemaorg.VideoGame import VideoGame
from pydantic2_schemaorg.VideoGameClip import VideoGameClip
from pydantic2_schemaorg.VideoGameSeries import VideoGameSeries
from pydantic2_schemaorg.VideoObject import VideoObject
from pydantic2_schemaorg.VideoObjectSnapshot import VideoObjectSnapshot
from pydantic2_schemaorg.VisualArtwork import VisualArtwork
from pydantic2_schemaorg.WPAdBlock import WPAdBlock
from pydantic2_schemaorg.WPFooter import WPFooter
from pydantic2_schemaorg.WPHeader import WPHeader
from pydantic2_schemaorg.WPSideBar import WPSideBar
from pydantic2_schemaorg.WebApplication import WebApplication
from pydantic2_schemaorg.WebContent import WebContent
from pydantic2_schemaorg.WebPage import WebPage
from pydantic2_schemaorg.WebPageElement import WebPageElement
from pydantic2_schemaorg.WebSite import WebSite
from pydantic2_schemaorg._3DModel import _3DModel

MediaObjectType = Union[
    MediaObject,
    AmpStory,
    AudioObject,
    AudioObjectSnapshot,
    Audiobook,
    Barcode,
    DataDownload,
    ImageObject,
    ImageObjectSnapshot,
    LegislationObject,
    MusicVideoObject,
    TextObject,
    VideoObject,
    VideoObjectSnapshot,
    _3DModel,
]

SoftwareApplicationType = Union[
    SoftwareApplication,
    MobileApplication,
    VideoGame,
    WebApplication,
]

CreativeWorkType = Union[
    # every MediaObject and SoftwareApplication is a CreativeWork
    MediaObjectType,
    SoftwareApplicationType,
    APIReference,
    AboutPage,
    AdvertiserContentArticle,
    AnalysisNewsArticle,
    Answer,
    ArchiveComponent,
    Article,
    AskPublicNewsArticle,
    Atlas,
    BackgroundNewsArticle,
    Blog,
    BlogPosting,
    Book,
    BookSeries,
    CategoryCodeSet,
    Certification,
    Chapter,
    CheckoutPage,
    Claim,
    ClaimReview,
    Clip,
    Code,
    Collection,
    CollectionPage,
    ComicCoverArt,
    ComicIssue,
    ComicSeries,
    ComicStory,
    Comment,
    CompleteDataFeed,
    ContactPage,
    Conversation,
    CorrectionComment,
    Course,
    CoverArt,
    CreativeWorkSeason,
    CreativeWorkSeries,
    CriticReview,
    DataCatalog,
    DataFeed,
    Dataset,
    DefinedTermSet,
    Diet,
    DigitalDocument,
    DiscussionForumPosting,
    Drawing,
    EducationalOccupationalCredential,
    EmailMessage,
    EmployerReview,
    Episode,
    ExercisePlan,
    FAQPage,
    Game,
    Guide,
    HealthTopicContent,
    HowTo,
    HowToDirection,
    HowToSection,
    HowToStep,
    HowToTip,
    HyperToc,
    HyperTocEntry,
    ImageGallery,
    ItemPage,
    LearningResource,
    Legislation,
    LiveBlogPosting,
    Manuscript,
    Map,
    MathSolver,
    MediaGallery,
    MediaReview,
    MediaReviewItem,
    MedicalScholarlyArticle,
    MedicalWebPage,
    Menu,
    MenuSection,
    Message,
    Movie,
    MovieClip,
    MovieSeries,
    MusicAlbum,
    MusicComposition,
    MusicPlaylist,
    MusicRecording,
    MusicRelease,
    NewsArticle,
    Newspaper,
    NoteDigitalDocument,
    OpinionNewsArticle,
    Painting,
    Periodical,
    Photograph,
    Play,
    PodcastEpisode,
    PodcastSeason,
    PodcastSeries,
    Poster,
    PresentationDigitalDocument,
    ProductCollection,
    ProfilePage,
    PublicationIssue,
    PublicationVolume,
    QAPage,
    Question,
    Quiz,
    Quotation,
    RadioClip,
    RadioEpisode,
    RadioSeason,
    RadioSeries,
    RealEstateListing,
    Recipe,
    Recommendation,
    Report,
    ReportageNewsArticle,
    Review,
    ReviewNewsArticle,
    SatiricalArticle,
    ScholarlyArticle,
    Sculpture,
    SearchResultsPage,
    Season,
    SheetMusic,
    ShortStory,
    SiteNavigationElement,
    SocialMediaPosting,
    SoftwareSourceCode,
    SpecialAnnouncement,
    SpreadsheetDigitalDocument,
    Statement,
    Syllabus,
    TVClip,
    TVEpisode,
    TVSeason,
    TVSeries,
    Table,
    TechArticle,
    TextDigitalDocument,
    Thesis,
    UserReview,
    VideoGallery,
    VideoGameClip,
    VideoGameSeries,
    VisualArtwork,
    WPAdBlock,
    WPFooter,
    WPHeader,
    WPSideBar,
    WebContent,
    WebPage,
    WebPageElement,
    WebSite,
]
