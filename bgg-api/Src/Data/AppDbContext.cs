using Microsoft.EntityFrameworkCore;

using BGGAPI.Src.Entities;

namespace BGGAPI.Src.Data;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<BoardGame> BoardGames { get; set; } = default!;

    public DbSet<Category> Categories { get; set; } = default!;
    public DbSet<Mechanic> Mechanics { get; set; } = default!;
    public DbSet<Family> Families { get; set; } = default!;
    public DbSet<BoardGameType> BoardGameTypes { get; set; } = default!;

    public DbSet<AlternativeName> BoardGameAlternativeNames { get; set; } = default!;
    public DbSet<BoardGameVersion> BoardGameVersions { get; set; } = default!;
    public DbSet<Credit> Credits { get; set; } = default!;
    public DbSet<Expansion> Expansions { get; set; } = default!;
    public DbSet<Reimplements> Reimplements { get; set; } = default!;
    public DbSet<Rank> Ranks { get; set; } = default!;
    public DbSet<ShopOffer> ShopOffers { get; set; } = default!;
    public DbSet<Recommendation> BoardGameRecommendations { get; set; } = default!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<BoardGame>(entity =>
        {
            entity.HasIndex(boardGame => boardGame.Name);
            entity.HasIndex(boardGame => boardGame.YearPublished);
            entity.HasIndex(boardGame => boardGame.AverageRating);
            entity.HasIndex(boardGame => boardGame.BayesAverageRating);

            entity.HasMany(boardGame => boardGame.AlternativeNames)
                .WithOne(alternativeName => alternativeName.BoardGame)
                .HasForeignKey(alternativeName => alternativeName.BoardGameId);

            entity.HasMany(boardGame => boardGame.Credits)
                .WithOne(credit => credit.BoardGame)
                .HasForeignKey(credit => credit.BoardGameId);

            entity.HasMany(boardGame => boardGame.Expansions)
                .WithOne(expansion => expansion.BoardGame)
                .HasForeignKey(expansion => expansion.BoardGameId);

            entity.HasMany(boardGame => boardGame.Reimplements)
                .WithOne(reimplements => reimplements.BoardGame)
                .HasForeignKey(reimplements => reimplements.BoardGameId);

            entity.HasMany(boardGame => boardGame.Ranks)
                .WithOne(rank => rank.BoardGame)
                .HasForeignKey(rank => rank.BoardGameId);

            entity.HasMany(boardGame => boardGame.ShopOffers)
                .WithOne(shopOffer => shopOffer.BoardGame)
                .HasForeignKey(shopOffer => shopOffer.BoardGameId);

            entity.HasMany(boardGame => boardGame.Versions)
                .WithOne(version => version.BoardGame)
                .HasForeignKey(version => version.BoardGameId);

            entity.HasMany(boardGame => boardGame.RecommendationsFromThis)
                .WithOne(recommendation => recommendation.SeedBoardGame)
                .HasForeignKey(recommendation => recommendation.SeedBoardGameId)
                .OnDelete(DeleteBehavior.NoAction);

            entity.HasMany(boardGame => boardGame.RecommendationsToThis)
                .WithOne(recommendation => recommendation.RecommendedBoardGame)
                .HasForeignKey(recommendation => recommendation.RecommendedBoardGameId)
                .OnDelete(DeleteBehavior.NoAction);

            entity.HasMany(boardGame => boardGame.Categories)
                .WithMany(category => category.BoardGameCategories)
                .UsingEntity<Dictionary<string, object>>(
                    "BoardGameCategory",
                    right => right.HasOne<Category>().WithMany().HasForeignKey("CategoryId"),
                    left => left.HasOne<BoardGame>().WithMany().HasForeignKey("BoardGameId"),
                    join =>
                    {
                        join.HasKey("BoardGameId", "CategoryId");
                        join.HasIndex("CategoryId");
                    });

            entity.HasMany(boardGame => boardGame.Mechanics)
                .WithMany(mechanic => mechanic.BoardGames)
                .UsingEntity<Dictionary<string, object>>(
                    "BoardGameMechanic",
                    right => right.HasOne<Mechanic>().WithMany().HasForeignKey("MechanicId"),
                    left => left.HasOne<BoardGame>().WithMany().HasForeignKey("BoardGameId"),
                    join =>
                    {
                        join.HasKey("BoardGameId", "MechanicId");
                        join.HasIndex("MechanicId");
                    });

            entity.HasMany(boardGame => boardGame.Families)
                .WithMany(family => family.BoardGameCategories)
                .UsingEntity<Dictionary<string, object>>(
                    "BoardGameFamily",
                    right => right.HasOne<Family>().WithMany().HasForeignKey("FamilyId"),
                    left => left.HasOne<BoardGame>().WithMany().HasForeignKey("BoardGameId"),
                    join =>
                    {
                        join.HasKey("BoardGameId", "FamilyId");
                        join.HasIndex("FamilyId");
                    });

            entity.HasMany(boardGame => boardGame.Types)
                .WithMany(boardgameType => boardgameType.BoardGames)
                .UsingEntity<Dictionary<string, object>>(
                    "BoardGameBoardGameType",
                    right => right.HasOne<BoardGameType>().WithMany().HasForeignKey("BoardGameTypeId"),
                    left => left.HasOne<BoardGame>().WithMany().HasForeignKey("BoardGameId"),
                    join =>
                    {
                        join.HasKey("BoardGameId", "BoardGameTypeId");
                        join.HasIndex("BoardGameTypeId");
                    });
        });

        modelBuilder.Entity<AlternativeName>(entity =>
        {
            entity.HasIndex(alternativeName => new { alternativeName.BoardGameId, alternativeName.Name }).IsUnique();
            entity.HasIndex(alternativeName => alternativeName.Name);
        });

        modelBuilder.Entity<Category>(entity =>
        {
            entity.HasIndex(category => category.Name).IsUnique();
        });

        modelBuilder.Entity<Mechanic>(entity =>
        {
            entity.HasIndex(mechanic => mechanic.Name).IsUnique();
        });

        modelBuilder.Entity<Family>(entity =>
        {
            entity.HasIndex(family => family.Name).IsUnique();
        });

        modelBuilder.Entity<BoardGameType>(entity =>
        {
            entity.HasIndex(boardgameType => boardgameType.Name).IsUnique();
        });

        modelBuilder.Entity<Rank>(entity =>
        {
            entity.HasIndex(rank => new { rank.BoardGameId, rank.Category }).IsUnique();
        });

        modelBuilder.Entity<ShopOffer>(entity =>
        {
            entity.HasIndex(shopOffer => new { shopOffer.BoardGameId, shopOffer.Seller });
        });

        modelBuilder.Entity<Recommendation>(entity =>
        {
            entity.HasIndex(recommendation => new { recommendation.SeedBoardGameId, recommendation.RecommendedBoardGameId }).IsUnique();
            entity.HasIndex(recommendation => recommendation.SeedBoardGameId);
            entity.HasIndex(recommendation => recommendation.RecommendedBoardGameId);
            entity.HasIndex(recommendation => new { recommendation.SeedBoardGameId, recommendation.Score });
        });

    }

    public override int SaveChanges()
    {
        var now = DateTimeOffset.UtcNow;

        TouchRelatedEntitiesUpdatedAtSync(now);
        DoCustomEntityPreparations(now);
        return base.SaveChanges();
    }

    public override int SaveChanges(bool acceptAllChangesOnSuccess)
    {
        var now = DateTimeOffset.UtcNow;

        TouchRelatedEntitiesUpdatedAtSync(now);
        DoCustomEntityPreparations(now);
        return base.SaveChanges(acceptAllChangesOnSuccess);
    }

    public override async Task<int> SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        var now = DateTimeOffset.UtcNow;

        await TouchRelatedEntitiesUpdatedAtAsync(now, cancellationToken);
        DoCustomEntityPreparations(now);
        return await base.SaveChangesAsync(cancellationToken);
    }

    private void CollectBoardGameIds(out HashSet<int> boardgameIds)
    {
        var entries = ChangeTracker.Entries()
            .Where(e => e.Entity is AlternativeName ||
                        e.Entity is BoardGameVersion ||
                        e.Entity is Credit ||
                        e.Entity is Expansion ||
                        e.Entity is Reimplements ||
                        e.Entity is Rank ||
                        e.Entity is ShopOffer ||
                        e.Entity is Recommendation)
            .ToList();

        boardgameIds = new HashSet<int>();

        foreach (var entry in entries)
        {
            switch (entry.Entity)
            {
                case AlternativeName alternativeName:
                    if (alternativeName.BoardGameId > 0)
                        boardgameIds.Add(alternativeName.BoardGameId);
                    break;
                case BoardGameVersion version:
                    if (version.BoardGameId > 0)
                        boardgameIds.Add(version.BoardGameId);
                    break;
                case Credit credit:
                    if (credit.BoardGameId > 0)
                        boardgameIds.Add(credit.BoardGameId);
                    break;
                case Expansion expansion:
                    if (expansion.BoardGameId > 0)
                        boardgameIds.Add(expansion.BoardGameId);
                    break;
                case Reimplements reimplements:
                    if (reimplements.BoardGameId > 0)
                        boardgameIds.Add(reimplements.BoardGameId);
                    break;
                case Rank rank:
                    if (rank.BoardGameId > 0)
                        boardgameIds.Add(rank.BoardGameId);
                    break;
                case ShopOffer shopOffer:
                    if (shopOffer.BoardGameId > 0)
                        boardgameIds.Add(shopOffer.BoardGameId);
                    break;
                case Recommendation recommendation:
                    if (recommendation.SeedBoardGameId > 0)
                        boardgameIds.Add(recommendation.SeedBoardGameId);
                    if (recommendation.RecommendedBoardGameId > 0)
                        boardgameIds.Add(recommendation.RecommendedBoardGameId);
                    break;
            }
        }
    }

    private void TouchRelatedEntitiesUpdatedAtSync(DateTimeOffset now)
    {
        CollectBoardGameIds(out var boardgameIds);

        foreach (var boardgameId in boardgameIds.ToList())
        {
            var trackedBoardGame = ChangeTracker.Entries<BoardGame>().FirstOrDefault(e => e.Entity.Id == boardgameId);
            if (trackedBoardGame != null)
            {
                trackedBoardGame.Entity.UpdatedAt = now;
            }
            else
            {
                var boardgame = Set<BoardGame>().FirstOrDefault(b => b.Id == boardgameId);
                if (boardgame != null)
                {
                    boardgame.UpdatedAt = now;
                    Update(boardgame);
                }
            }
        }
    }

    private async Task TouchRelatedEntitiesUpdatedAtAsync(DateTimeOffset now, CancellationToken cancellationToken)
    {
        CollectBoardGameIds(out var boardgameIds);

        foreach (var boardgameId in boardgameIds.ToList())
        {
            var trackedBoardGame = ChangeTracker.Entries<BoardGame>().FirstOrDefault(e => e.Entity.Id == boardgameId);
            if (trackedBoardGame != null)
            {
                trackedBoardGame.Entity.UpdatedAt = now;
            }
            else
            {
                var boardgame = await Set<BoardGame>().FirstOrDefaultAsync(b => b.Id == boardgameId, cancellationToken);
                if (boardgame != null)
                {
                    boardgame.UpdatedAt = now;
                    Update(boardgame);
                }
            }
        }


    }

    private void DoCustomEntityPreparations(DateTimeOffset now)
    {
        var modifiedEntitiesWithTrackDate = ChangeTracker.Entries().Where(c => c.State == EntityState.Modified);

        foreach (var entityEntry in modifiedEntitiesWithTrackDate)
            if (entityEntry.Properties.Any(c => c.Metadata.Name == "UpdatedAt"))
                entityEntry.Property("UpdatedAt").CurrentValue = now;
    }

}